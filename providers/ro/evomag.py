import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from core.http_pool import get_shared_session

class EvoMagProvider(BaseProvider):
    store_id = "evomag_ro"
    store_name = "evoMAG"
    country_code = "RO"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "cpu"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.evomag.ro/cauta/{encoded}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.evomag.ro/"
        }

        try:
            s = get_shared_session()
            r = s.get(url, headers=headers, timeout=5.0)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.select(".sn-product") or soup.select(".product_box") or soup.select(".npi_content")

                for idx, item in enumerate(items[:20]):
                    title_el = item.select_one(".npi_name") or item.select_one(".product_name") or item.select_one("a[title]")
                    if not title_el:
                        continue
                    title = title_el.text.strip()
                    product_url = title_el.get("href", url)
                    if product_url.startswith("/"):
                        product_url = "https://www.evomag.ro" + product_url

                    price_el = item.select_one(".real_price") or item.select_one(".money_val") or item.select_one(".price")
                    if not price_el:
                        continue
                    
                    raw_price = price_el.text.strip()
                    clean = re.sub(r"[^\d,\.]", "", raw_price).replace(".", "").replace(",", ".")
                    try:
                        price = float(clean)
                    except ValueError:
                        price = 0.0

                    img_el = item.select_one("img")
                    img_url = img_el.get("src") or img_el.get("data-src") if img_el else None
                    if img_url and img_url.startswith("/"):
                        img_url = "https://www.evomag.ro" + img_url

                    stock_el = item.select_one(".npi_stock") or item.select_one(".stock") or item.select_one(".sn-stock")
                    stock_text = stock_el.text.strip() if stock_el else "In Stoc"
                    
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    badge_text = stock_text

                    if "epuizat" in stock_text.lower() or "indisponibil" in stock_text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"
                    elif "limitat" in stock_text.lower():
                        stock_level = StockLevel.LOW_STOCK
                        badge_text = "Limited Stock"

                    results.append(
                        StoreResult(
                            id=f"evomag_{idx}_{hash(product_url) % 100000}",
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
                            delivery_info="Express Delivery / Showroom Mihai Bravu",
                            category=ProductCategory.TECH_HARDWARE
                        )
                    )
        except Exception as e:
            print(f"[evoMAG] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
