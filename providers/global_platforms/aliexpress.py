import re
import json
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class AliExpressProvider(BaseProvider):
    store_id = "aliexpress"
    store_name = "AliExpress"
    country_code = "GLOBAL"
    category = ProductCategory.GENERAL
    store_icon = "globe"

    def __init__(self, country_code: str = "US"):
        self.country_code = country_code.upper()
        if self.country_code == "RO":
            self.currency = "EUR"
            self.region_code = "RO"
        elif self.country_code == "AU":
            self.currency = "AUD"
            self.region_code = "AU"
        elif self.country_code in ["DE", "FR", "IT", "ES", "NL"]:
            self.currency = "EUR"
            self.region_code = self.country_code
        elif self.country_code in ["GB", "UK"]:
            self.currency = "GBP"
            self.region_code = "GB"
        else:
            self.currency = "USD"
            self.region_code = "US"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.aliexpress.com/w/wholesale-{encoded}.html"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.aliexpress.com/",
            "Cookie": f"aep_usuc_f=site=glo&c_tp={self.currency}&region={self.region_code}&b_locale=en_US"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=9)
                if r.status_code == 200:
                    results = self._parse_html(r.text, query, url)
        except Exception as e:
            print(f"[AliExpress] Error querying {query}: {e}")

        return results

    def _parse_html(self, html: str, query: str, search_url: str) -> List[StoreResult]:
        items: List[StoreResult] = []

        # Strategy 1: Look for JSON state in script tags
        script_matches = re.findall(r"window\._init_data_\s*=\s*(\{.+?\});</script>", html, re.DOTALL)
        if not script_matches:
            script_matches = re.findall(r"window\.runParams\s*=\s*(\{.+?\});</script>", html, re.DOTALL)

        if script_matches:
            try:
                data = json.loads(script_matches[0])
                # Traverse known paths
                product_list = []
                if "data" in data and "root" in data["data"]:
                    mods = data["data"]["root"].get("fields", {}).get("mods", {})
                    product_list = mods.get("itemList", {}).get("content", [])
                elif "items" in data:
                    product_list = data["items"]

                for idx, p in enumerate(product_list[:16]):
                    title = p.get("title", {}).get("displayTitle") or p.get("productTitle")
                    if not title:
                        continue

                    # Price
                    price = 0.0
                    price_info = p.get("prices", {}).get("salePrice", {})
                    if "minPrice" in price_info:
                        price = float(price_info["minPrice"])
                    elif "formattedPrice" in price_info:
                        raw = re.sub(r"[^\d,\.]", "", str(price_info["formattedPrice"])).replace(",", ".")
                        try:
                            price = float(raw)
                        except ValueError:
                            price = 0.0

                    prod_id = p.get("productId") or idx
                    detail_url = p.get("productDetailUrl")
                    if detail_url:
                        if detail_url.startswith("//"):
                            detail_url = "https:" + detail_url
                    else:
                        detail_url = f"https://www.aliexpress.com/item/{prod_id}.html"

                    img_url = p.get("image", {}).get("imgUrl")
                    if img_url and img_url.startswith("//"):
                        img_url = "https:" + img_url

                    orders_count = p.get("trade", {}).get("tradeDesc", "Factory Direct")

                    items.append(
                        StoreResult(
                            id=f"ali_{prod_id}_{idx}",
                            store_name="AliExpress",
                            store_icon="globe",
                            country_code=self.country_code,
                            title=title,
                            price=price,
                            currency=self.currency,
                            in_stock=True,
                            stock_level=StockLevel.ONLINE_STOCK,
                            stock_badge_text=f"Online Stock ({orders_count})",
                            product_url=detail_url,
                            image_url=img_url,
                            delivery_info="AliExpress Standard Shipping",
                            category=ProductCategory.GENERAL
                        )
                    )
            except Exception as json_err:
                print(f"[AliExpress] Error parsing JSON state: {json_err}")

        if items:
            return items

        # Strategy 2: Beautiful Soup DOM parsing
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.search-item-card-wrapper-open-item, div[data-spm='search_item'], a.search-card-item")

        for idx, card in enumerate(cards[:15]):
            title_el = card.select_one("h1, h3, [title], .multi--titleText--")
            if not title_el:
                continue
            title = title_el.get("title") or title_el.text.strip()

            price_el = card.select_one(".multi--price-sale--, .search-card-price, span.price")
            price = 0.0
            if price_el:
                raw = re.sub(r"[^\d,\.]", "", price_el.text.strip()).replace(",", ".")
                try:
                    price = float(raw)
                except ValueError:
                    price = 0.0

            link_el = card if card.name == 'a' else card.select_one("a[href]")
            prod_url = search_url
            if link_el and link_el.get("href"):
                href = link_el["href"]
                prod_url = ("https:" + href) if href.startswith("//") else (("https://www.aliexpress.com" + href) if href.startswith("/") else href)

            img_el = card.select_one("img")
            img_url = img_el.get("src") or img_el.get("data-src") if img_el else None
            if img_url and img_url.startswith("//"):
                img_url = "https:" + img_url

            items.append(
                StoreResult(
                    id=f"ali_dom_{idx}_{abs(hash(prod_url)) % 100000}",
                    store_name="AliExpress",
                    store_icon="globe",
                    country_code=self.country_code,
                    title=title,
                    price=price,
                    currency=self.currency,
                    in_stock=True,
                    stock_level=StockLevel.ONLINE_STOCK,
                    stock_badge_text="Online Stock (Choice)",
                    product_url=prod_url,
                    image_url=img_url,
                    delivery_info="AliExpress Buyer Protection",
                    category=ProductCategory.GENERAL
                )
            )

        return items
