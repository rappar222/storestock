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
        if AutoMarketProvider.is_car_query(query):
            return results

        clean_query = query.strip()
        encoded = urllib.parse.quote_plus(clean_query)
        url = (
            f"https://www.temu.com/search_result.html?"
            f"search_key={encoded}&search_method=user&refer_page_el_sn=200010&srch_enter_source=top_search_entrance_10005"
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ro;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.temu.com/",
            "Cookie": f"region={self.region}; currency={self.currency}; language=en;"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(url, headers=headers, timeout=12)
                if r.status_code == 200:
                    results = self._parse_html(r.text, clean_query, url)
                else:
                    print(f"[Temu] Returned HTTP {r.status_code} for query: {clean_query}")
        except Exception as e:
            print(f"[Temu] Error querying {clean_query}: {e}")

        return results

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

    def _find_goods_recursive(self, obj: Any) -> List[Dict]:
        """
        Recursively traverse any nested JSON structure to find product items.
        Matches goods_name, goodsName, title, or short_name with price and goods_id.
        """
        found = []
        if isinstance(obj, dict):
            has_name = any(k in obj for k in ["goods_name", "goodsName", "title", "short_name", "goods_title"])
            has_id = any(k in obj for k in ["goods_id", "goodsId", "link_url", "linkUrl", "goods_url"])
            if has_name and has_id:
                found.append(obj)
            else:
                for k, v in obj.items():
                    if k in ["goodsList", "goods_list", "items", "data", "list", "products", "cardList", "itemListElement"] and isinstance(v, list):
                        for item in v:
                            found.extend(self._find_goods_recursive(item))
                    elif isinstance(v, (dict, list)):
                        found.extend(self._find_goods_recursive(v))
        elif isinstance(obj, list):
            for item in obj:
                found.extend(self._find_goods_recursive(item))
        return found

    def _parse_html(self, html: str, query: str, search_url: str) -> List[StoreResult]:
        items: List[StoreResult] = []
        parsed_goods: List[Dict] = []

        # 1. Look for known state variables using balanced JSON extraction
        for prefix in ["window.__INITIAL_STATE__", "window.rawData", "window._SSR_DATA_", "window.__PRELOADED_STATE__"]:
            idx = 0
            while True:
                idx = html.find(prefix, idx)
                if idx == -1:
                    break
                data = self._extract_balanced_json(html, idx + len(prefix))
                if data:
                    goods = self._find_goods_recursive(data)
                    if goods:
                        parsed_goods.extend(goods)
                idx += len(prefix)

        # 2. Extract JSON from script tags (including application/ld+json and application/json)
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script"):
            script_type = script.get("type", "")
            script_id = script.get("id", "")
            content = script.string or script.text or ""

            if not content:
                continue

            # Case A: JSON-LD (Schema.org Product/ItemList)
            if "application/ld+json" in script_type:
                try:
                    ld_data = json.loads(content)
                    if isinstance(ld_data, dict):
                        if ld_data.get("@type") == "ItemList":
                            for elem in ld_data.get("itemListElement", []):
                                prod = elem.get("item", {})
                                if prod.get("@type") == "Product":
                                    parsed_goods.append({
                                        "goods_name": prod.get("name"),
                                        "goods_id": str(elem.get("position", len(parsed_goods))),
                                        "price": prod.get("offers", {}).get("price", 0.0),
                                        "thumb_url": prod.get("image"),
                                        "link_url": prod.get("url")
                                    })
                        elif ld_data.get("@type") == "Product":
                            parsed_goods.append({
                                "goods_name": ld_data.get("name"),
                                "goods_id": str(len(parsed_goods)),
                                "price": ld_data.get("offers", {}).get("price", 0.0),
                                "thumb_url": ld_data.get("image"),
                                "link_url": ld_data.get("url")
                            })
                except Exception:
                    pass

            # Case B: Embedded application/json or preloaded data scripts
            elif "json" in script_type or any(k in script_id for k in ["preloaded", "state", "data", "NEXT"]):
                if "goods" in content or "price" in content:
                    try:
                        data = json.loads(content.strip())
                        goods = self._find_goods_recursive(data)
                        if goods:
                            parsed_goods.extend(goods)
                    except Exception:
                        pass

        # 3. Convert discovered JSON items to StoreResult
        seen_ids = set()
        for idx, g in enumerate(parsed_goods[:25]):
            title = g.get("goods_name") or g.get("goodsName") or g.get("title") or g.get("goods_title")
            if not title or len(str(title).strip()) < 3:
                continue

            goods_id = str(g.get("goods_id") or g.get("goodsId") or idx)
            if goods_id in seen_ids:
                continue
            seen_ids.add(goods_id)

            # Extract Price
            price = 0.0
            price_info = g.get("price_info", {})
            if isinstance(price_info, dict) and "price" in price_info:
                p_val = float(price_info["price"])
                price = (p_val / 100.0) if p_val > 1000 else p_val
            elif "sale_price" in g and g["sale_price"]:
                price = float(g["sale_price"])
            elif "price" in g and g["price"]:
                try:
                    p_val = float(g["price"])
                    price = (p_val / 100.0) if p_val > 1000 else p_val
                except (ValueError, TypeError):
                    price = 0.0

            thumb = g.get("thumb_url") or g.get("thumbUrl") or g.get("image_url") or g.get("imageUrl") or g.get("image")
            if thumb and str(thumb).startswith("//"):
                thumb = "https:" + str(thumb)

            link = g.get("link_url") or g.get("linkUrl") or g.get("url") or f"/goods-{goods_id}.html"
            link_str = str(link)
            prod_url = f"https://www.temu.com{link_str}" if link_str.startswith("/") else (
                link_str if link_str.startswith("http") else f"https://www.temu.com/{link_str}"
            )

            sold_text = g.get("sales_tip") or g.get("salesTip") or "In Stock"

            items.append(
                StoreResult(
                    id=f"temu_{goods_id}_{idx}",
                    store_name="Temu",
                    store_icon="tag",
                    country_code=self.country_code,
                    title=str(title).strip(),
                    price=price,
                    currency=self.currency,
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text=f"In Stock ({sold_text})",
                    product_url=prod_url,
                    image_url=thumb,
                    delivery_info="Temu Express Delivery & Price Guarantee",
                    category=ProductCategory.GENERAL
                )
            )

        if items:
            return items

        # 4. DOM Fallback: Find cards via HTML tags and attributes
        card_elements = soup.select(
            "a[href*='goods'], a[href*='-g-'], a[aria-label], div[data-goods-id], div[class*='goods']"
        )

        for idx, card in enumerate(card_elements[:20]):
            title = None
            if card.get("aria-label"):
                title = card["aria-label"].strip()
            if not title:
                title_el = card.select_one("h2, h3, [title], [class*='title'], [class*='goodsName']")
                if title_el:
                    title = title_el.get("title") or title_el.text.strip()
            if not title:
                img_el = card.select_one("img[alt]")
                if img_el and img_el.get("alt"):
                    title = img_el["alt"].strip()

            if not title or len(title) < 4:
                continue

            price = 0.0
            price_el = card.select_one("[class*='price'], span")
            if price_el:
                raw_p = re.sub(r"[^\d,\.]", "", price_el.text.strip()).replace(",", ".")
                try:
                    price = float(raw_p)
                except ValueError:
                    price = 0.0

            href = card.get("href") or (card.select_one("a[href]")["href"] if card.select_one("a[href]") else "")
            prod_url = f"https://www.temu.com{href}" if href.startswith("/") else (href if href.startswith("http") else search_url)

            img_el = card.select_one("img")
            img_url = img_el.get("src") or img_el.get("data-src") if img_el else None
            if img_url and img_url.startswith("//"):
                img_url = "https:" + img_url

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
                    stock_badge_text="In Stock",
                    product_url=prod_url,
                    image_url=img_url,
                    delivery_info="Temu Express Delivery",
                    category=ProductCategory.GENERAL
                )
            )

        return items
