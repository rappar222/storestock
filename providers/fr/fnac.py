import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class FnacFRProvider(BaseProvider):
    store_id = "fnac_fr"
    store_name = "Fnac France"
    country_code = "FR"
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
        url = f"https://www.fnac.com/SearchResult/ResultList.aspx?Search={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Referer": "https://www.fnac.com/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select(".Article-item, .f-productCard, div[data-article-id]")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one(".Article-title, a.Article-titleUrl, h2 a, [data-automation-id='product-title']")
                        if not title_el:
                            continue
                        title = title_el.text.strip()

                        # Price
                        price_el = card.select_one(".userPrice, .f-price, span.price, .Article-price")
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
                            prod_url = f"https://www.fnac.com{h}" if h.startswith("/") else h

                        img_el = card.select_one("img[src]")
                        img_url = img_el.get("src") if img_el else None

                        results.append(StoreResult(
                            id=f"fnac_fr_{idx}_{abs(hash(title)) % 100000}",
                            store_name="Fnac France",
                            store_icon="shopping-bag",
                            country_code="FR",
                            title=title,
                            price=price,
                            currency="EUR",
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text="En Stock (Retrait 1h en magasin Fnac)",
                            store_branch="Fnac Paris Montparnasse / Lyon / Marseille",
                            product_url=prod_url,
                            image_url=img_url,
                            category=ProductCategory.TECH_HARDWARE,
                            delivery_info="Retrait gratuit 1h en magasin ou Colissimo"
                        ))
        except Exception as e:
            print(f"[Fnac FR] Error querying {query}: {e}")

        return results
