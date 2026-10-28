import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class AlibabaProvider(BaseProvider):
    store_id = "alibaba"
    store_name = "Alibaba Wholesale"
    country_code = "GLOBAL"
    category = ProductCategory.GENERAL
    store_icon = "factory"

    def __init__(self, country_code: str = "US"):
        self.country_code = country_code.upper()
        if self.country_code == "RO":
            self.currency = "USD"
        elif self.country_code == "AU":
            self.currency = "USD"
        elif self.country_code in ["DE", "FR", "IT", "ES", "NL"]:
            self.currency = "EUR"
        elif self.country_code in ["GB", "UK"]:
            self.currency = "GBP"
        else:
            self.currency = "USD"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&SearchText={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.alibaba.com/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=9)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select("div.fy23-search-card, div.m-gallery-product-item, div[data-content='product'], div.list-no-v2-outer")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one(".search-card-e-title, .elements-title-normal, h2 a, [title]")
                        if not title_el:
                            continue
                        title = title_el.get("title") or title_el.text.strip()

                        # Alibaba price: usually like "$10.00 - $15.00 / piece" or "$250.00 / set"
                        price_el = card.select_one(".search-card-e-price-main, .elements-offer-price-normal, .price, .search-card-m-price")
                        price = 0.0
                        price_str = ""
                        if price_el:
                            price_str = price_el.text.strip()
                            clean = re.findall(r"\d+(?:\.\d+)?", price_str.replace(",", ""))
                            if clean:
                                try:
                                    price = float(clean[0])
                                except ValueError:
                                    price = 0.0

                        # Min Order Quantity
                        moq_el = card.select_one(".search-card-e-min-order, .element-order-num, .min-order")
                        moq = moq_el.text.strip() if moq_el else "MOQ: 1 piece"

                        link_el = card.select_one("a[href*='/product-detail/'], a[href*='alibaba.com']")
                        prod_url = url
                        if link_el and link_el.get("href"):
                            h = link_el["href"]
                            prod_url = ("https:" + h) if h.startswith("//") else (("https://www.alibaba.com" + h) if h.startswith("/") else h)

                        img_el = card.select_one("img.search-card-e-slider__img, img")
                        img_url = img_el.get("src") or img_el.get("data-src") if img_el else None
                        if img_url and img_url.startswith("//"):
                            img_url = "https:" + img_url

                        results.append(
                            StoreResult(
                                id=f"ali_b2b_{idx}_{abs(hash(prod_url)) % 100000}",
                                store_name="Alibaba B2B",
                                store_icon="factory",
                                country_code=self.country_code,
                                title=title,
                                price=price,
                                currency=self.currency,
                                in_stock=True,
                                stock_level=StockLevel.IN_STOCK,
                                stock_badge_text=f"Wholesale ({moq})",
                                product_url=prod_url,
                                image_url=img_url,
                                delivery_info=f"Factory Direct / {moq}",
                                category=ProductCategory.GENERAL
                            )
                        )
        except Exception as e:
            print(f"[Alibaba] Error querying {query}: {e}")

        return results
