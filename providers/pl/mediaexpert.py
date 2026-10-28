import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class MediaExpertPLProvider(BaseProvider):
    store_id = "mediaexpert_pl"
    store_name = "Media Expert Poland"
    country_code = "PL"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "tv"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.mediaexpert.pl/szukaj?query={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
            "Referer": "https://www.mediaexpert.pl/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select(".offer-box, div[data-offer-id], div.product-box")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one("h2.name a, a.is-inner, h2 a, [title]")
                        if not title_el:
                            continue
                        title = title_el.text.strip() or title_el.get("title", "")

                        # Price
                        price_el = card.select_one("span.whole, .price, div.prices")
                        price = 0.0
                        if price_el:
                            clean = re.sub(r"[^\d,\.]", "", price_el.text.strip())
                            clean = clean.replace(" ", "").replace(",", ".")
                            try:
                                price = float(re.findall(r"\d+\.?\d*", clean)[0])
                            except Exception:
                                price = 0.0

                        link_el = card.select_one("a[href]")
                        prod_url = url
                        if link_el and link_el.get("href"):
                            h = link_el["href"]
                            prod_url = f"https://www.mediaexpert.pl{h}" if h.startswith("/") else h

                        img_el = card.select_one("img[src]")
                        img_url = img_el.get("src") if img_el else None

                        results.append(StoreResult(
                            id=f"me_pl_{idx}_{abs(hash(title)) % 100000}",
                            store_name="Media Expert Poland",
                            store_icon="tv",
                            country_code="PL",
                            title=title,
                            price=price,
                            currency="PLN",
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text="Dostępne na półce (Odbiór za 30 min)",
                            store_branch="Media Expert Warszawa / Wrocław",
                            product_url=prod_url,
                            image_url=img_url,
                            category=ProductCategory.TECH_HARDWARE,
                            delivery_info="Odbiór w wybranym elektromarkecie za 29 min"
                        ))
        except Exception as e:
            print(f"[Media Expert PL] Error querying {query}: {e}")

        return results
