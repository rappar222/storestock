import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from core.http_pool import get_shared_session

class PCGarageProvider(BaseProvider):
    store_id = "pcgarage_ro"
    store_name = "PC Garage"
    country_code = "RO"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "cpu"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.pcgarage.ro/cauta/{encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.pcgarage.ro/"
        }

        try:
            s = get_shared_session()
            r = s.get(url, headers=headers, timeout=2.0)
            if r.status_code != 200:
                return results

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select(".product_box_container")

                for idx, card in enumerate(cards[:24]):
                    name_el = card.select_one(".product_box_name")
                    if not name_el:
                        continue
                    title = name_el.text.strip()

                    price_el = card.select_one(".price") or card.select_one(".price_num")
                    if not price_el:
                        continue
                    
                    raw_price = price_el.text.strip()
                    clean_price = re.sub(r"[^\d,\.]", "", raw_price)
                    clean_price = clean_price.replace(".", "").replace(",", ".")
                    try:
                        price = float(clean_price)
                    except ValueError:
                        price = 0.0

                    link_el = card.select_one("a[href]")
                    product_url = link_el["href"] if link_el else url

                    img_el = card.select_one("img")
                    img_url = img_el.get("src") if img_el else None

                    stock_el = card.select_one(".product_box_availability")
                    raw_stock = stock_el.text.strip() if stock_el else "In Stoc"

                    raw_stock_lower = raw_stock.lower()
                    if "epuizat" in raw_stock_lower or "lipsa" in raw_stock_lower:
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"
                    elif "limitat" in raw_stock_lower:
                        in_stock = True
                        stock_level = StockLevel.LOW_STOCK
                        badge_text = raw_stock
                    else:
                        in_stock = True
                        stock_level = StockLevel.IN_STOCK
                        badge_text = raw_stock

                    results.append(
                        StoreResult(
                            id=f"pcgarage_{idx}_{hash(product_url) % 100000}",
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
                            delivery_info="Warehouse Express / Store Pickup",
                            category=ProductCategory.TECH_HARDWARE
                        )
                    )
        except Exception as e:
            print(f"[PCGarage] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
