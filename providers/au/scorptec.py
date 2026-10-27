import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class ScorptecProvider(BaseProvider):
    store_id = "scorptec"
    store_name = "Scorptec Computers"
    country_code = "AU"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "cpu"

    async def search(self, query: str) -> List[StoreResult]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.scorptec.com.au/product/search?q={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code != 200:
                    return results

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select(".product-card") or soup.select(".product-item") or soup.select(".detail-wrapper")

                for idx, c in enumerate(cards[:15]):
                    title_el = c.select_one(".product-title a") or c.select_one("h3 a") or c.select_one("a.title")
                    if not title_el:
                        continue
                    title = title_el.text.strip()
                    rel_url = title_el.get("href", "")
                    prod_url = f"https://www.scorptec.com.au{rel_url}" if rel_url.startswith("/") else rel_url

                    # Price
                    price_el = c.select_one(".product-price") or c.select_one(".price")
                    price = 0.0
                    if price_el:
                        raw = price_el.text.strip().replace("$", "").replace(",", "")
                        try:
                            price = float(re.findall(r"\d+\.?\d*", raw)[0])
                        except Exception:
                            price = 0.0

                    # Stock
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    badge_text = "In Stock (Sydney / Melb Pickup)"
                    if "out of stock" in c.text.lower() or "sold out" in c.text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"
                    elif "in stock" in c.text.lower():
                        badge_text = "In Stock at Branch"

                    img_el = c.select_one("img.product-img") or c.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    results.append(StoreResult(
                        id=f"scorp_{idx}_{hash(title) % 100000}",
                        store_name=self.store_name,
                        store_icon=self.store_icon,
                        country_code=self.country_code,
                        title=title,
                        price=price,
                        currency="AUD",
                        in_stock=in_stock,
                        stock_level=stock_level,
                        stock_badge_text=badge_text,
                        product_url=prod_url,
                        image_url=img_url,
                        category=self.category,
                        delivery_info="Scorptec Store Click & Collect / Australia Express"
                    ))
        except Exception as e:
            print(f"[Scorptec] Search error for '{query}': {e}")

        return results
