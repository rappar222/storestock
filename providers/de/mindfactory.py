import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class MindfactoryDEProvider(BaseProvider):
    store_id = "mindfactory_de"
    store_name = "Mindfactory"
    country_code = "DE"
    category = ProductCategory.TECH_HARDWARE
    store_icon = "cpu"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.mindfactory.de/search_result.php?search_query={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8",
            "Referer": "https://www.mindfactory.de/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select("div.ProductList-Product, div.p-item, div.product-box")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one("a.p-complete-link, h2.p-name, .p-title")
                        if not title_el:
                            continue
                        title = title_el.text.strip()

                        # Price
                        price_el = card.select_one(".pprice, .p-price, div.price")
                        price = 0.0
                        if price_el:
                            clean = re.sub(r"[^\d,\.]", "", price_el.text.strip())
                            clean = clean.replace(".", "").replace(",", ".")
                            try:
                                price = float(re.findall(r"\d+\.?\d*", clean)[0])
                            except Exception:
                                price = 0.0

                        link_el = card.select_one("a[href*='product_info.php'], a[href]")
                        prod_url = url
                        if link_el and link_el.get("href"):
                            h = link_el["href"]
                            prod_url = f"https://www.mindfactory.de/{h}" if not h.startswith("http") else h

                        img_el = card.select_one("img[src]")
                        img_url = img_el.get("src") if img_el else None

                        results.append(StoreResult(
                            id=f"mf_de_{idx}_{abs(hash(title)) % 100000}",
                            store_name="Mindfactory AG",
                            store_icon="cpu",
                            country_code="DE",
                            title=title,
                            price=price,
                            currency="EUR",
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text="Lagernd (Verfügbar)",
                            store_branch="Zentrallager Wilhelmshaven",
                            product_url=prod_url,
                            image_url=img_url,
                            category=ProductCategory.TECH_HARDWARE,
                            delivery_info="Midnight Shopping Gratisversand / DHL Express"
                        ))
        except Exception as e:
            print(f"[Mindfactory DE] Error querying {query}: {e}")

        return results
