import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class WalmartProvider(BaseProvider):
    store_id = "walmart"
    store_name = "Walmart"
    country_code = "US"
    category = ProductCategory.GENERAL
    store_icon = "shopping-cart"

    async def search(self, query: str) -> List[StoreResult]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.walmart.com/search?q={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code != 200:
                    return results

                soup = BeautifulSoup(r.text, "html.parser")
                tiles = soup.select("div[data-item-id]")

                for idx, t in enumerate(tiles[:15]):
                    title_el = t.select_one("span[data-automation-id='product-title']") or t.select_one("a.w-100 span")
                    link_el = t.select_one("a[link-identifier]") or t.select_one("a[href]")
                    if not title_el or not link_el:
                        continue
                    
                    title = title_el.text.strip()
                    rel_url = link_el.get("href", "")
                    prod_url = f"https://www.walmart.com{rel_url}" if rel_url.startswith("/") else rel_url

                    # Price
                    price_el = t.select_one("div[data-automation-id='product-price'] span.w_iUH7") or t.select_one("span[class*='price']")
                    price = 0.0
                    if price_el:
                        raw = price_el.text.strip().replace("$", "").replace(",", "")
                        try:
                            price = float(re.findall(r"\d+\.?\d*", raw)[0])
                        except Exception:
                            price = 0.0

                    # Stock
                    badge_text = "In Stock (Pickup & Delivery)"
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    if "out of stock" in t.text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"

                    img_el = t.select_one("img[data-testid='productTileImage']") or t.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    results.append(StoreResult(
                        id=f"wm_{idx}_{hash(title) % 100000}",
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
                        delivery_info="Walmart Curbside Pickup & 2-Day Shipping"
                    ))
        except Exception as e:
            print(f"[Walmart] Search error for '{query}': {e}")

        return results
