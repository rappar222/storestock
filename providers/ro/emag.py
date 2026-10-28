import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
try:
    from selectolax.parser import HTMLParser
    HAS_SELECTOLAX = True
except ImportError:
    HAS_SELECTOLAX = False
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from core.http_pool import get_shared_session

class EmagProvider(BaseProvider):
    store_id = "emag_ro"
    store_name = "eMAG"
    country_code = "RO"
    category = ProductCategory.GENERAL
    store_icon = "shopping-cart"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.emag.ro/search/{encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.emag.ro/"
        }

        try:
            s = get_shared_session()
            r = s.get(url, headers=headers, timeout=2.5)
            if r.status_code != 200:
                return results

            if HAS_SELECTOLAX:
                tree = HTMLParser(r.text)
                raw_cards = tree.css(".card-item")
                for idx, card in enumerate(raw_cards[:24]):
                    title_el = card.css_first(".card-v2-title")
                    if not title_el:
                        continue
                    title = title_el.text(strip=True)

                    price_el = card.css_first(".product-new-price")
                    if not price_el:
                        continue
                    raw_price = price_el.text(strip=True)
                    clean_price_str = re.sub(r"[^\d,\.]", "", raw_price).replace(".", "").replace(",", ".")
                    try:
                        price = float(clean_price_str)
                    except ValueError:
                        price = 0.0

                    link_el = card.css_first("a[href]")
                    product_url = link_el.attributes.get("href", url) if link_el else url
                    if product_url.startswith("/"):
                        product_url = "https://www.emag.ro" + product_url

                    img_el = card.css_first("img")
                    img_url = None
                    if img_el:
                        img_url = img_el.attributes.get("src") or img_el.attributes.get("data-src")

                    btn = card.css_first("button[type=submit]") or card.css_first(".btn")
                    btn_text = btn.text(strip=True).lower() if btn else ""
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    stock_badge_text = "In Stock"

                    if "adauga in cos" in btn_text or "precomanda" in btn_text:
                        in_stock = True
                        stock_level = StockLevel.IN_STOCK if "adauga" in btn_text else StockLevel.PREORDER
                    elif "resigilat" in btn_text:
                        in_stock = True
                        stock_level = StockLevel.LOW_STOCK
                        stock_badge_text = "Resealed"
                    elif "indisponibil" in btn_text or "stoc epuizat" in btn_text:
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        stock_badge_text = "Out of Stock"

                    results.append(StoreResult(
                        id=f"emag_{idx}_{hash(product_url) % 100000}",
                        store_name=self.store_name,
                        store_icon=self.store_icon,
                        country_code=self.country_code,
                        title=title,
                        price=price,
                        currency="RON",
                        in_stock=in_stock,
                        stock_level=stock_level,
                        stock_badge_text=stock_badge_text,
                        product_url=product_url,
                        image_url=img_url,
                        category=self.category,
                        delivery_info="Delivery by eMAG / Genius"
                    ))
                return results

            # Fallback to BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.select(".card-item")

                for idx, card in enumerate(cards[:24]):
                    title_el = card.select_one(".card-v2-title")
                    if not title_el:
                        continue
                    title = title_el.text.strip()
                    
                    price_el = card.select_one(".product-new-price")
                    if not price_el:
                        continue
                    
                    # Parse price like "3.539,99 Lei" or "14,50 Lei"
                    raw_price = price_el.text.strip()
                    clean_price_str = re.sub(r"[^\d,\.]", "", raw_price)
                    clean_price_str = clean_price_str.replace(".", "").replace(",", ".")
                    try:
                        price = float(clean_price_str)
                    except ValueError:
                        price = 0.0

                    link_el = card.select_one("a[href]")
                    product_url = link_el["href"] if link_el else url
                    if product_url.startswith("/"):
                        product_url = "https://www.emag.ro" + product_url

                    img_el = card.select_one("img")
                    img_url = None
                    if img_el:
                        img_url = img_el.get("src") or img_el.get("data-src")

                    # Check stock / order availability
                    btn = card.select_one("button[type=submit]") or card.select_one(".btn")
                    btn_text = btn.text.strip().lower() if btn else ""
                    
                    in_stock = True
                    stock_level = StockLevel.IN_STOCK
                    badge_text = "In Stock"

                    if "adauga in cos" in btn_text:
                        in_stock = True
                        stock_level = StockLevel.IN_STOCK
                        badge_text = "In Stock (Order Now)"
                    elif "stoc epuizat" in card.text.lower() or "notifica-ma" in btn_text:
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"
                    elif "in stoc" in card.text.lower():
                        in_stock = True
                        stock_level = StockLevel.IN_STOCK
                        badge_text = "In Stock"

                    # Check seller / delivery badge
                    delivery_info = "eMAG Genius / Direct Delivery"
                    if "partener" in card.text.lower() or "vandut de" in card.text.lower():
                        delivery_info = "Marketplace Partner"

                    results.append(
                        StoreResult(
                            id=f"emag_{idx}_{hash(product_url) % 100000}",
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
                            delivery_info=delivery_info,
                            category=ProductCategory.GENERAL
                        )
                    )
        except Exception as e:
            print(f"[EmagProvider] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
