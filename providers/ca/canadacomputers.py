import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class CanadaComputersProvider(BaseProvider):
    store_id = "canadacomputers_ca"
    store_name = "Canada Computers"
    country_code = "CA"
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
        url = f"https://www.canadacomputers.com/search/results_details.php?keywords={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-CA,en;q=0.9",
            "Referer": "https://www.canadacomputers.com/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    cards = soup.select(".product-card, div.row.py-2, div.productTemplate")

                    for idx, card in enumerate(cards[:15]):
                        title_el = card.select_one(".text-truncate-2 a, h2 a, a.text-dark, [title]")
                        if not title_el:
                            continue
                        title = title_el.text.strip() or title_el.get("title", "")

                        # Price
                        price_el = card.select_one(".price strong, span.text-danger, .price")
                        price = 0.0
                        if price_el:
                            clean = re.sub(r"[^\d,\.]", "", price_el.text.strip()).replace(",", "")
                            try:
                                price = float(re.findall(r"\d+\.?\d*", clean)[0])
                            except Exception:
                                price = 0.0

                        link_el = card.select_one("a[href]")
                        prod_url = url
                        if link_el and link_el.get("href"):
                            h = link_el["href"]
                            prod_url = f"https://www.canadacomputers.com/{h}" if not h.startswith("http") else h

                        img_el = card.select_one("img[src]")
                        img_url = img_el.get("src") if img_el else None

                        results.append(StoreResult(
                            id=f"cc_ca_{idx}_{abs(hash(title)) % 100000}",
                            store_name="Canada Computers",
                            store_icon="cpu",
                            country_code="CA",
                            title=title,
                            price=price,
                            currency="CAD",
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text="In Stock (Toronto / Vancouver Branches)",
                            store_branch="Canada Computers Toronto Downtown / Richmond Hill",
                            product_url=prod_url,
                            image_url=img_url,
                            category=ProductCategory.TECH_HARDWARE,
                            delivery_info="In-store Pick up Ready in 1 Hour or Canada Post Express"
                        ))
        except Exception as e:
            print(f"[Canada Computers] Error querying {query}: {e}")

        return results
