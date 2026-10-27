import urllib.parse
from typing import List
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class AuchanProvider(BaseProvider):
    store_id = "auchan_ro"
    store_name = "Auchan Hypermarket"
    country_code = "RO"
    category = ProductCategory.GROCERIES
    store_icon = "shopping-cart"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded_query = urllib.parse.quote(query)
        # VTEX Search API
        url = f"https://www.auchan.ro/api/catalog_system/pub/products/search?ft={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.auchan.ro/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=6)
                if r.status_code not in (200, 206):
                    return results

                products = r.json()
                if not isinstance(products, list):
                    return results

                for idx, p in enumerate(products[:20]):
                    name = p.get("productName")
                    if not name:
                        continue

                    items = p.get("items", [])
                    if not items:
                        continue

                    first_item = items[0]
                    sellers = first_item.get("sellers", [])
                    comm = sellers[0].get("commertialOffer", {}) if sellers else {}

                    price = float(comm.get("Price", 0.0))
                    qty = comm.get("AvailableQuantity", 0)
                    in_stock = qty > 0

                    images = first_item.get("images", [])
                    image_url = images[0].get("imageUrl") if images else None
                    product_url = p.get("link", "https://www.auchan.ro")

                    if in_stock:
                        stock_level = StockLevel.IN_STOCK
                        badge_text = f"In Stock ({qty} available)" if qty < 20 else "In Stock (Hypermarket)"
                    else:
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"

                    results.append(
                        StoreResult(
                            id=f"auchan_{idx}_{p.get('productId', hash(product_url) % 10000)}",
                            store_name=self.store_name,
                            store_icon=self.store_icon,
                            country_code=self.country_code,
                            title=name,
                            price=price,
                            currency="RON",
                            in_stock=in_stock,
                            stock_level=stock_level,
                            stock_badge_text=badge_text,
                            stock_qty=qty,
                            product_url=product_url,
                            image_url=image_url,
                            brand=p.get("brand"),
                            delivery_info="Same-Day Delivery & Drive Pickup",
                            category=ProductCategory.GROCERIES
                        )
                    )
        except Exception as e:
            print(f"[Auchan] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
