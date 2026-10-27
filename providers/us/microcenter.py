import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class MicroCenterProvider(BaseProvider):
    store_id = "microcenter"
    store_name = "Micro Center"
    country_code = "US"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "cpu"

    async def search(self, query: str) -> List[StoreResult]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.microcenter.com/search/search_results.aspx?Ntt={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code != 200:
                    return results

                soup = BeautifulSoup(r.text, "html.parser")
                products = soup.select("li.product_wrapper")

                for idx, p in enumerate(products[:15]):
                    title_el = p.select_one("div.normal a") or p.select_one("h2 a")
                    if not title_el:
                        continue
                    title = title_el.text.strip()
                    rel_url = title_el.get("href", "")
                    prod_url = f"https://www.microcenter.com{rel_url}" if rel_url.startswith("/") else rel_url

                    # Price
                    price_el = p.select_one("span[itemprop='price']") or p.select_one(".price span")
                    price = 0.0
                    if price_el:
                        raw = price_el.text.strip().replace("$", "").replace(",", "")
                        try:
                            price = float(raw)
                        except ValueError:
                            price = 0.0

                    # Stock level & shelf availability
                    stock_el = p.select_one("div.stock") or p.select_one(".inventory")
                    stock_text = stock_el.text.strip() if stock_el else "In Stock (Online / Store Pickup)"
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK

                    if "out of stock" in stock_text.lower() or "sold out" in stock_text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Sold Out"
                    elif "in stock" in stock_text.lower():
                        in_stock = True
                        stock_level = StockLevel.IN_STOCK
                        badge_text = stock_text[:35]
                    else:
                        badge_text = "Available in Store"

                    # Image
                    img_el = p.select_one("img.SearchResultProductImage") or p.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    results.append(StoreResult(
                        id=f"mc_{idx}_{hash(title) % 100000}",
                        store_name=self.store_name,
                        store_icon=self.store_icon,
                        country_code=self.country_code,
                        title=title,
                        price=price,
                        currency="USD",
                        in_stock=in_stock,
                        stock_level=stock_level,
                        stock_badge_text=badge_text,
                        product_url=prod_url,
                        image_url=img_url,
                        category=self.category,
                        delivery_info="In-Store Pickup (18 min) & Shipping"
                    ))
        except Exception as e:
            print(f"[MicroCenter] Search error for '{query}': {e}")

        return results
