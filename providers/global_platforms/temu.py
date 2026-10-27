import re
import json
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider

class TemuProvider(BaseProvider):
    store_id = "temu"
    store_name = "Temu"
    country_code = "GLOBAL"
    category = ProductCategory.GENERAL
    store_icon = "tag"

    def __init__(self, country_code: str = "US"):
        self.country_code = country_code.upper()
        if self.country_code == "RO":
            self.currency = "RON"
            self.region = "ro"
        elif self.country_code == "AU":
            self.currency = "AUD"
            self.region = "au"
        elif self.country_code in ["DE", "FR", "IT", "ES", "NL"]:
            self.currency = "EUR"
            self.region = self.country_code.lower()
        elif self.country_code in ["GB", "UK"]:
            self.currency = "GBP"
            self.region = "uk"
        else:
            self.currency = "USD"
            self.region = "us"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.temu.com/search_result.html?search_key={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.temu.com/",
            "Cookie": f"region={self.region}; currency={self.currency};"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=9)
                if r.status_code == 200:
                    results = self._parse_html(r.text, query, url)
        except Exception as e:
            print(f"[Temu] Error querying {query}: {e}")

        # Fallback card if Temu anti-bot / challenge renders empty
        if not results:
            results.append(
                StoreResult(
                    id=f"temu_search_{abs(hash(query)) % 100000}",
                    store_name="Temu",
                    store_icon="tag",
                    country_code=self.country_code,
                    title=f"Browse '{query}' on Temu (Direct Factory Wholesale)",
                    price=0.0,
                    currency=self.currency,
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text="In Stock (Global Warehouse)",
                    product_url=f"https://www.temu.com/search_result.html?search_key={encoded}",
                    image_url="https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=300&auto=format&fit=crop&q=60",
                    delivery_info="Temu Express Delivery & Price Match Guarantee",
                    category=ProductCategory.GENERAL
                )
            )

        return results

    def _parse_html(self, html: str, query: str, search_url: str) -> List[StoreResult]:
        items: List[StoreResult] = []

        # Check for window.rawData in HTML
        raw_match = re.search(r"window\.rawData\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
        if raw_match:
            try:
                data = json.loads(raw_match.group(1))
                store_data = data.get("store", {}) or data.get("data", {})
                goods_list = store_data.get("goodsList", []) or store_data.get("items", [])

                for idx, g in enumerate(goods_list[:16]):
                    title = g.get("goods_name") or g.get("title")
                    if not title:
                        continue

                    # Price
                    price = 0.0
                    price_info = g.get("price_info", {})
                    if "price" in price_info:
                        price = float(price_info["price"]) / 100.0 if float(price_info["price"]) > 1000 else float(price_info["price"])
                    elif "sale_price" in g:
                        price = float(g["sale_price"])

                    thumb = g.get("thumb_url") or g.get("image_url")
                    goods_id = g.get("goods_id", idx)
                    link = g.get("link_url", f"/goods-{goods_id}.html")
                    prod_url = f"https://www.temu.com{link}" if link.startswith("/") else link

                    sold_text = g.get("sales_tip", "Hot Item")

                    items.append(
                        StoreResult(
                            id=f"temu_{goods_id}_{idx}",
                            store_name="Temu",
                            store_icon="tag",
                            country_code=self.country_code,
                            title=title,
                            price=price,
                            currency=self.currency,
                            in_stock=True,
                            stock_level=StockLevel.IN_STOCK,
                            stock_badge_text=f"In Stock ({sold_text})",
                            product_url=prod_url,
                            image_url=thumb,
                            delivery_info="Temu Fast Shipping & Free Returns",
                            category=ProductCategory.GENERAL
                        )
                    )
            except Exception as e:
                print(f"[Temu] Error parsing rawData: {e}")

        if items:
            return items

        # Fallback to DOM parsing
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[data-goods-id], div.goods-card, div._26k5e_4b, a[href*='goods_id']")

        for idx, card in enumerate(cards[:15]):
            title_el = card.select_one("h2, h3, [title], .goods-title")
            if not title_el:
                continue
            title = title_el.get("title") or title_el.text.strip()

            price_el = card.select_one(".price, [class*='price'], ._26k5e_price")
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
                h = link_el["href"]
                prod_url = f"https://www.temu.com{h}" if h.startswith("/") else h

            img_el = card.select_one("img")
            img_url = img_el.get("src") or img_el.get("data-src") if img_el else None

            items.append(
                StoreResult(
                    id=f"temu_dom_{idx}_{abs(hash(prod_url)) % 100000}",
                    store_name="Temu",
                    store_icon="tag",
                    country_code=self.country_code,
                    title=title,
                    price=price,
                    currency=self.currency,
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text="In Stock (Direct Factory)",
                    product_url=prod_url,
                    image_url=img_url,
                    delivery_info="Temu Free Shipping",
                    category=ProductCategory.GENERAL
                )
            )

        return items
