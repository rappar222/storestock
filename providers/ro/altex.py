import urllib.parse
from typing import List
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class AltexProvider(BaseProvider):
    store_id = "altex_ro"
    store_name = "Altex"
    country_code = "RO"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "monitor"
    brand_header = "altex"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded_query = urllib.parse.quote(query)
        url = f"https://fenrir.altex.ro/v2/catalog/search/{encoded_query}"

        headers = {
            "User-Agent": "Altex/3.1.0 (Android 14; Mobile)",
            "Accept": "application/json",
            "x-brand": self.brand_header
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=6)
                if r.status_code != 200:
                    return results

                data = r.json()
                products = data.get("products", [])

                for idx, p in enumerate(products[:24]):
                    name = p.get("name")
                    if not name:
                        continue
                    
                    price = float(p.get("special_price") or p.get("price") or 0.0)
                    sku = p.get("sku", "")
                    url_key = p.get("url_key", "")
                    
                    product_url = f"https://altex.ro/{url_key}/cpd/{sku}" if url_key and sku else "https://altex.ro"
                    
                    raw_img = p.get("image")
                    image_url = f"https://lcdn.altex.ro{raw_img}" if raw_img else None

                    stock_status = p.get("stock_status", 1)
                    pickup_in_stock = p.get("pickup_is_in_stock", 0)
                    preorder_status = p.get("preorder_status", 0)

                    in_stock = stock_status == 1 or pickup_in_stock == 1
                    
                    if preorder_status == 1:
                        stock_level = StockLevel.PREORDER
                        badge_text = "Pre-order Available"
                    elif pickup_in_stock == 1 and stock_status == 0:
                        stock_level = StockLevel.STORE_PICKUP_ONLY
                        badge_text = "In Store Pickup Only"
                    elif in_stock:
                        stock_level = StockLevel.IN_STOCK
                        badge_text = "In Stock (Delivery & Pickup)"
                    else:
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"

                    results.append(
                        StoreResult(
                            id=f"{self.store_id}_{idx}_{sku}",
                            store_name=self.store_name,
                            store_icon=self.store_icon,
                            country_code=self.country_code,
                            title=name,
                            price=price,
                            currency="RON",
                            in_stock=in_stock,
                            stock_level=stock_level,
                            stock_badge_text=badge_text,
                            product_url=product_url,
                            image_url=image_url,
                            sku=sku,
                            delivery_info="Courier Delivery / 2h Store Pickup",
                            category=ProductCategory.TECH_HARDWARE
                        )
                    )
        except Exception as e:
            print(f"[{self.store_name}] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
