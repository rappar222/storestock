import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class CoolblueNLProvider(BaseProvider):
    store_id = "coolblue_nl"
    store_name = "Coolblue Netherlands"
    country_code = "NL"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "shopping-bag"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.coolblue.nl/zoeken?query={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
            "Referer": "https://www.coolblue.nl/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select(".product-card, div[data-product-id], div.product-card-container")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one("a.product-card__title, h3 a, [title]")
                        if not title_el:
                            continue
                        title = title_el.text.strip() or title_el.get("title", "")

                        # Price
                        price_el = card.select_one(".sales-price__current, span[class*='sales-price'], .sales-price")
                        price = 0.0
                        if price_el:
                            clean = re.sub(r"[^\d,\.]", "", price_el.text.strip())
                            clean = clean.replace(".", "").replace(",", ".")
                            try:
                                price = float(re.findall(r"\d+\.?\d*", clean)[0])
                            except Exception:
                                price = 0.0

                        link_el = card.select_one("a[href]")
                        prod_url = url
                        if link_el and link_el.get("href"):
                            h = link_el["href"]
                            prod_url = f"https://www.coolblue.nl{h}" if h.startswith("/") else h

                        img_el = card.select_one("img[src]")
                        img_url = img_el.get("src") if img_el else None

                        results.append(StoreResult(
                            id=f"cb_nl_{idx}_{abs(hash(title)) % 100000}",
                            store_name="Coolblue Netherlands",
                            store_icon="shopping-bag",
                            country_code="NL",
                            title=title,
                            price=price,
                            currency="EUR",
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text="Op voorraad in winkel (Amsterdam / Rotterdam)",
                            store_branch="Coolblue Amsterdam Zuidas / Den Haag",
                            product_url=prod_url,
                            image_url=img_url,
                            category=ProductCategory.TECH_HARDWARE,
                            delivery_info="Vandaag nog ophalen in de winkel of morgen gratis bezorgd"
                        ))
        except Exception as e:
            print(f"[Coolblue NL] Error querying {query}: {e}")

        return results
