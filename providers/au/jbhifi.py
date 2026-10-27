import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class JBHiFiProvider(BaseProvider):
    store_id = "jbhifi"
    store_name = "JB Hi-Fi"
    country_code = "AU"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "tv"

    async def search(self, query: str) -> List[StoreResult]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.jbhifi.com.au/search?query={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-AU,en;q=0.9"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code != 200:
                    return results

                soup = BeautifulSoup(r.text, "html.parser")
                tiles = soup.select("div[data-testid='product-card']") or soup.select(".product-tile")

                for idx, t in enumerate(tiles[:15]):
                    title_el = t.select_one("h3") or t.select_one("a.title") or t.select_one("span.product-title")
                    link_el = t.select_one("a[href]")
                    if not title_el or not link_el:
                        continue
                    
                    title = title_el.text.strip()
                    rel_url = link_el.get("href", "")
                    prod_url = f"https://www.jbhifi.com.au{rel_url}" if rel_url.startswith("/") else rel_url

                    price_el = t.select_one(".price") or t.select_one("span[data-testid='product-price']")
                    price = 0.0
                    if price_el:
                        raw = price_el.text.strip().replace("$", "").replace(",", "")
                        try:
                            price = float(re.findall(r"\d+\.?\d*", raw)[0])
                        except Exception:
                            price = 0.0

                    badge_text = "In Stock (1 Hr Store Pickup)"
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    if "out of stock" in t.text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"

                    img_el = t.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    results.append(StoreResult(
                        id=f"jb_{idx}_{hash(title) % 100000}",
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
                        delivery_info="JB Hi-Fi 1-Hour Click & Collect Across Australia"
                    ))
        except Exception as e:
            print(f"[JB Hi-Fi] Search error for '{query}': {e}")

        return results
