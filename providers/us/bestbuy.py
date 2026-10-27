import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class BestBuyProvider(BaseProvider):
    store_id = "bestbuy"
    store_name = "Best Buy"
    country_code = "US"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "shopping-bag"

    async def search(self, query: str) -> List[StoreResult]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded}"

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
                items = soup.select("li.sku-item")

                for idx, item in enumerate(items[:15]):
                    title_el = item.select_one("h4.sku-title a") or item.select_one(".sku-header a")
                    if not title_el:
                        continue
                    title = title_el.text.strip()
                    rel_url = title_el.get("href", "")
                    prod_url = f"https://www.bestbuy.com{rel_url}" if rel_url.startswith("/") else rel_url

                    # Price
                    price_el = item.select_one(".priceView-hero-price span") or item.select_one(".priceView-customer-price span")
                    price = 0.0
                    if price_el:
                        raw = price_el.text.strip().replace("$", "").replace(",", "")
                        try:
                            price = float(raw)
                        except ValueError:
                            price = 0.0

                    # Stock / Pickup status
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    badge_text = "In Stock (Pickup or Delivery)"
                    
                    fulfillment_el = item.select_one(".fulfillment-fulfillment-summary") or item.select_one(".fulfillment-summary")
                    if fulfillment_el and "sold out" in fulfillment_el.text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Sold Out"
                    elif fulfillment_el and "get it today" in fulfillment_el.text.lower():
                        badge_text = "Store Pickup Today"

                    # Image
                    img_el = item.select_one("img.product-image")
                    img_url = img_el.get("src") if img_el else None

                    results.append(StoreResult(
                        id=f"bb_{idx}_{hash(title) % 100000}",
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
                        delivery_info="Best Buy Store Pickup & Fast Delivery"
                    ))
        except Exception as e:
            print(f"[BestBuy] Search error for '{query}': {e}")

        return results
