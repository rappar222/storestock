import urllib.parse
from typing import List
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class GlovoExpressProvider(BaseProvider):
    """
    Simulates quick-commerce dark stores & local partners (Glovo Express, Bolt Market, Tazz)
    providing hyper-local 30-minute delivery for daily essentials & urgent needs.
    """
    store_id = "glovo_ro"
    store_name = "Glovo Express (30m Delivery)"
    country_code = "RO"
    category = ProductCategory.GROCERIES
    store_icon = "zap"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        q_lower = query.lower().strip()

        # Quick commerce catalog specializes in groceries, snacks, household, and urgent electronics
        is_grocery = any(k in q_lower for k in ["lapte", "paine", "cafea", "oua", "apa", "cola", "bere", "suc", "ciocolata", "unt", "iaurt", "fructe", "legume"])
        is_urgent_tech = any(k in q_lower for k in ["cablu", "incarcator", "charger", "baterie", "casti", "mouse", "stick", "usb", "adaptor"])

        if not (is_grocery or is_urgent_tech):
            # Glovo dark stores don't carry enterprise GPUs or heavy servers
            return results

        # Query live Auchan or Carrefour express items via VTEX
        encoded = urllib.parse.quote(query)
        url = f"https://www.auchan.ro/api/catalog_system/pub/products/search?ft={encoded}"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=6)
                if r.status_code in (200, 206):
                    items = r.json()
                    for idx, p in enumerate(items[:10]):
                        name = p.get("productName")
                        if not name:
                            continue
                        sub_items = p.get("items", [])
                        if not sub_items:
                            continue
                        comm = sub_items[0].get("sellers", [{}])[0].get("commertialOffer", {})
                        price = float(comm.get("Price", 0.0))
                        qty = comm.get("AvailableQuantity", 0)
                        
                        img = sub_items[0].get("images", [{}])[0].get("imageUrl") if sub_items[0].get("images") else None
                        link = p.get("link", "https://glovoapp.com")

                        results.append(
                            StoreResult(
                                id=f"glovo_{idx}_{hash(name) % 10000}",
                                store_name=self.store_name,
                                store_icon=self.store_icon,
                                country_code=self.country_code,
                                title=f"⚡ {name}",
                                price=round(price * 1.05, 2), # Slight quick-commerce markup
                                currency="RON",
                                in_stock=qty > 0,
                                stock_level=StockLevel.IN_STOCK if qty > 0 else StockLevel.OUT_OF_STOCK,
                                stock_badge_text="In Stock (30m Courier)",
                                stock_qty=qty,
                                product_url=link,
                                image_url=img,
                                delivery_info="🛵 Delivered to door in ~30 mins",
                                category=ProductCategory.GROCERIES
                            )
                        )
        except Exception as e:
            print(f"[GlovoExpress] Error: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
