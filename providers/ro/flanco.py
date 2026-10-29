import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from core.http_pool import get_shared_session

class FlancoProvider(BaseProvider):
    store_id = "flanco_ro"
    store_name = "Flanco"
    country_code = "RO"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "shopping-bag"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.flanco.ro/catalogsearch/result/?q={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.flanco.ro/"
        }

        try:
            s = get_shared_session()
            r = s.get(url, headers=headers, timeout=5.0)
            if r.status_code != 200:
                return results

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select(".product-item")

            for idx, item in enumerate(items[:20]):
                name_el = item.select_one(".product-item-link")
                if not name_el:
                    continue
                title = name_el.text.strip()
                product_url = name_el.get("href", url)

                price_el = item.select_one(".price")
                if not price_el:
                    continue

                raw_price = price_el.text.strip()
                clean_price = re.sub(r"[^\d,\.]", "", raw_price)
                clean_price = clean_price.replace(".", "").replace(",", ".")
                try:
                    price = float(clean_price)
                except ValueError:
                    price = 0.0

                img_el = item.select_one(".product-image-photo")
                img_url = img_el.get("src") if img_el else None

                in_stock = True
                stock_level = StockLevel.IN_STOCK
                badge_text = "In Stock (Delivery / In-store)"

                if "epuizat" in item.text.lower():
                    in_stock = False
                    stock_level = StockLevel.OUT_OF_STOCK
                    badge_text = "Out of Stock"

                results.append(
                    StoreResult(
                        id=f"flanco_{idx}_{hash(product_url) % 100000}",
                        store_name=self.store_name,
                        store_icon=self.store_icon,
                        country_code=self.country_code,
                        title=title,
                        price=price,
                        currency="RON",
                        in_stock=in_stock,
                        stock_level=stock_level,
                        stock_badge_text=badge_text,
                        product_url=product_url,
                        image_url=img_url,
                        delivery_info="Standard Delivery & Store Pickup",
                        category=ProductCategory.TECH_HARDWARE
                    )
                )
        except Exception as e:
            print(f"[Flanco] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
