import re
import json
import urllib.parse
from typing import List, Dict, Any, Optional
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

    def _clean_price(self, val: Any) -> float:
        """
        Robust price extractor handling numbers, dicts, and multi-currency strings.
        Supports both dot and comma decimal representations (e.g. 1,299.99 or 14,99 €).
        """
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict):
            for k in ["minPrice", "salePrice", "formattedPrice", "value", "price", "amount", "currentPrice", "originalPrice", "actMinPrice"]:
                if k in val and val[k] is not None:
                    p = self._clean_price(val[k])
                    if p > 0:
                        return p
            return 0.0

        text = str(val).strip()
        if not text:
            return 0.0

        # Remove currency words/symbols but keep digits, commas, and dots
        clean = re.sub(r"[^\d,\.]", "", text)
        if not clean:
            return 0.0

        if "," in clean and "." in clean:
            if clean.rfind(".") > clean.rfind(","):
                # 1,234.56
                clean = clean.replace(",", "")
            else:
                # 1.234,56
                clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            # 14,99
            parts = clean.split(",")
            if len(parts) == 2 and len(parts[1]) in [1, 2]:
                clean = f"{parts[0]}.{parts[1]}"
            else:
                clean = clean.replace(",", "")

        try:
            return float(clean)
        except ValueError:
            return 0.0

    def _extract_balanced_json(self, text: str, start_index: int) -> Optional[dict]:
        """
        Extracts a valid JSON object by tracking brace balance and string quotes,
        preventing broken extraction from nested curly braces.
        """
        brace_start = text.find("{", start_index)
        if brace_start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for i in range(brace_start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[brace_start:i+1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            return None
        return None

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if AutoMarketProvider.is_car_query(query):
            return results

        clean_query = query.strip()
        encoded = urllib.parse.quote_plus(clean_query)
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
                r = s.get(url, headers=headers, timeout=1.5)
                if r.status_code == 200:
                    results = self._parse_html(r.text, clean_query, url)
                else:
                    print(f"[AliExpress] Returned HTTP {r.status_code} for query: {clean_query}")
        except Exception as e:
            print(f"[AliExpress] Error querying {clean_query}: {e}")

        return results

    def _parse_html(self, html: str, query: str, search_url: str) -> List[StoreResult]:
        items: List[StoreResult] = []

        # Strategy 1: Balanced JSON state extraction from script tags
        patterns = [
            "window._init_data_ =",
            "window.runParams =",
            "window.__PRELOADED_STATE__ =",
            "window.__INITIAL_DATA__ ="
        ]

        data = None
        for pattern in patterns:
            pos = html.find(pattern)
            if pos != -1:
                extracted = self._extract_balanced_json(html, pos + len(pattern))
                if extracted and isinstance(extracted, dict):
                    data = extracted
                    break

        if data:
            try:
                product_list = []
                if "data" in data and isinstance(data["data"], dict) and "root" in data["data"]:
                    mods = data["data"]["root"].get("fields", {}).get("mods", {})
                    product_list = mods.get("itemList", {}).get("content", [])
                elif "items" in data and isinstance(data["items"], list):
                    product_list = data["items"]
                elif "resultList" in data and isinstance(data["resultList"], list):
                    product_list = data["resultList"]
                elif "products" in data and isinstance(data["products"], list):
                    product_list = data["products"]

                for idx, p in enumerate(product_list[:20]):
                    title = (
                        p.get("title", {}).get("displayTitle") or 
                        p.get("productTitle") or 
                        p.get("title") or 
                        p.get("subject")
                    )
                    if not title or len(str(title).strip()) < 3:
                        continue

                    title = str(title).strip()

                    # Extract price using robust multi-field cleaner
                    price = 0.0
                    for price_candidate in [
                        p.get("prices", {}).get("salePrice"),
                        p.get("prices", {}).get("minPrice"),
                        p.get("prices", {}).get("formattedPrice"),
                        p.get("prices", {}).get("originalPrice"),
                        p.get("prices"),
                        p.get("price"),
                        p.get("salePrice"),
                        p.get("minPrice"),
                        p.get("actMinPrice"),
                        p.get("promotionPrice"),
                        p.get("itemPrice")
                    ]:
                        price = self._clean_price(price_candidate)
                        if price > 0:
                            break

                    prod_id = p.get("productId") or p.get("itemId") or idx
                    detail_url = p.get("productDetailUrl") or p.get("itemDetailUrl")
                    if detail_url:
                        if detail_url.startswith("//"):
                            detail_url = "https:" + detail_url
                    else:
                        detail_url = f"https://www.aliexpress.com/item/{prod_id}.html"

                    img_url = (
                        p.get("image", {}).get("imgUrl") or 
                        p.get("imgUrl") or 
                        p.get("imageUrl") or 
                        p.get("image")
                    )
                    if isinstance(img_url, str) and img_url.startswith("//"):
                        img_url = "https:" + img_url

                    trade_info = p.get("trade", {})
                    orders_count = trade_info.get("tradeDesc") if isinstance(trade_info, dict) else "Factory Direct"

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
                            stock_badge_text=f"Online Stock ({orders_count or 'Choice'})",
                            product_url=detail_url,
                            image_url=img_url,
                            delivery_info="AliExpress Standard Shipping",
                            category=ProductCategory.GENERAL
                        )
                    )
            except Exception as json_err:
                print(f"[AliExpress] Error reading product list from JSON state: {json_err}")

        if items:
            return items

        # Strategy 2: Modern BeautifulSoup DOM parsing fallback
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(
            "div.search-item-card-wrapper-open-item, "
            "div[data-spm='search_item'], "
            "a.search-card-item, "
            "div[class*='search-card-item'], "
            "div[class*='multi--content--'], "
            "div[class*='list--gallery--'] a"
        )

        for idx, card in enumerate(cards[:20]):
            title_el = card.select_one(
                "h1, h3, [title], .multi--titleText--, [class*='titleText'], [class*='item-title']"
            )
            if not title_el:
                continue
            title = title_el.get("title") or title_el.text.strip()
            if not title or len(title) < 3:
                continue

            # Price extraction from DOM
            price_el = card.select_one(
                ".multi--price-sale--, "
                "[class*='price-sale'], "
                "[class*='salePrice'], "
                "[class*='currentPrice'], "
                "[class*='search-card-price'], "
                "[class*='item-price'], "
                "[class*='price--'], "
                "span.price, "
                "span.money"
            )
            price = 0.0
            if price_el:
                price = self._clean_price(price_el.text)

            link_el = card if card.name == 'a' else card.select_one("a[href]")
            prod_url = search_url
            if link_el and link_el.get("href"):
                href = link_el["href"]
                prod_url = ("https:" + href) if href.startswith("//") else (("https://www.aliexpress.com" + href) if href.startswith("/") else href)

            img_el = card.select_one("img[src], img[data-src]")
            img_url = None
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src")
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
