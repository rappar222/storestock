import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class AmazonProvider(BaseProvider):
    store_id = "amazon_global"
    store_name = "Amazon"
    country_code = "US"
    category = ProductCategory.GENERAL
    store_icon = "package"

    def __init__(self, country_code: str = "US"):
        self.country_code = country_code
        if country_code == "DE":
            self.domain = "amazon.de"
            self.currency = "EUR"
            self.store_name = "Amazon DE"
        elif country_code == "GB" or country_code == "UK":
            self.domain = "amazon.co.uk"
            self.currency = "GBP"
            self.store_name = "Amazon UK"
        elif country_code == "RO":
            self.domain = "amazon.de"
            self.currency = "EUR"
            self.store_name = "Amazon (EU Direct)"
        elif country_code == "AU":
            self.domain = "amazon.com.au"
            self.currency = "AUD"
            self.store_name = "Amazon Australia"
        else:
            self.domain = "amazon.com"
            self.currency = "USD"
            self.store_name = "Amazon US"

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.{self.domain}/s?k={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"https://www.{self.domain}/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=1.5)
                if r.status_code != 200:
                    return results

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("div[data-component-type=s-search-result]")

                for idx, card in enumerate(cards[:15]):
                    title_el = card.select_one("h2 span") or card.select_one("h2")
                    if not title_el:
                        continue
                    title = title_el.text.strip()

                    price_el = card.select_one(".a-price .a-offscreen") or card.select_one(".a-price")
                    price = 0.0
                    currency = self.currency
                    if price_el:
                        raw_price = price_el.text.strip()
                        # Extract currency if RON or $ or €
                        if "RON" in raw_price:
                            currency = "RON"
                        elif "€" in raw_price:
                            currency = "EUR"
                        elif "$" in raw_price:
                            currency = "USD"
                        elif "£" in raw_price:
                            currency = "GBP"

                        clean_price = re.sub(r"[^\d,\.]", "", raw_price)
                        clean_price = clean_price.replace(",", ".")
                        # Handle multi dots if any
                        parts = clean_price.split(".")
                        if len(parts) > 2:
                            clean_price = "".join(parts[:-1]) + "." + parts[-1]
                        try:
                            price = float(clean_price)
                        except ValueError:
                            price = 0.0

                    link_el = card.select_one("h2 a[href]") or card.select_one("a.a-link-normal[href]")
                    product_url = f"https://www.{self.domain}{link_el['href']}" if link_el else url

                    img_el = card.select_one("img.s-image")
                    img_url = img_el.get("src") if img_el else None

                    in_stock = True
                    stock_level = StockLevel.ONLINE_STOCK
                    badge_text = "Online Stock (Amazon Global)"

                    if "currently unavailable" in card.text.lower():
                        in_stock = False
                        stock_level = StockLevel.OUT_OF_STOCK
                        badge_text = "Out of Stock"

                    results.append(
                        StoreResult(
                            id=f"amz_{idx}_{hash(product_url) % 100000}",
                            store_name=self.store_name,
                            store_icon=self.store_icon,
                            country_code=self.country_code,
                            title=title,
                            price=price,
                            currency=currency,
                            in_stock=in_stock,
                            stock_level=stock_level,
                            stock_badge_text=badge_text,
                            product_url=product_url,
                            image_url=img_url,
                            delivery_info="Amazon Global Shipping",
                            category=ProductCategory.GENERAL
                        )
                    )
        except Exception as e:
            print(f"[{self.store_name}] Error querying: {e}")

        return results

    async def search(self, query: str) -> List[StoreResult]:
        return await asyncio.to_thread(self._sync_search, query)
