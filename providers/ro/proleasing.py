import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from curl_cffi import requests
import asyncio
from core.schema import StoreResult, StockLevel, ProductCategory
from providers.base import BaseProvider
from providers.cars.auto_market import AutoMarketProvider

class ProleasingProvider(BaseProvider):
    """
    Proleasing Motors Romania (Official BMW Premium Selection, Ford & Certified Pre-Owned Dealership).
    """
    store_id = "proleasing_ro"
    store_name = "Proleasing Motors"
    country_code = "RO"
    category = ProductCategory.AUTOMOTIVE
    store_icon = "car"

    def __init__(self):
        self.currency = "EUR"

    async def search(self, query: str) -> List[StoreResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query)

    def _sync_search(self, query: str) -> List[StoreResult]:
        results: List[StoreResult] = []
        if not AutoMarketProvider.is_car_query(query):
            return results

        clean_query = query.strip()
        encoded = urllib.parse.quote_plus(clean_query)

        # 1. Primary endpoint: Autovit Proleasing official dealer portal
        dealer_url = f"https://proleasing.autovit.ro/cars?q={encoded}"
        catalog_url = f"https://www.rulate-proleasing.ro/auto-rulate/?s={encoded}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://proleasing.autovit.ro/"
        }

        try:
            with requests.Session(impersonate="chrome124") as s:
                r = s.get(dealer_url, headers=headers, timeout=9)
                if r.status_code == 200:
                    results = self._parse_autovit_dealer_html(r.text, clean_query)
        except Exception as e:
            print(f"[Proleasing] Error querying dealer portal: {e}")

        # If zero parsed from dealer portal, try official rulate-proleasing portal
        if not results:
            try:
                with requests.Session(impersonate="chrome124") as s:
                    r2 = s.get(catalog_url, headers=headers, timeout=9)
                    if r2.status_code == 200:
                        results = self._parse_rulate_portal_html(r2.text, clean_query)
            except Exception as e:
                print(f"[Proleasing] Error querying catalog portal: {e}")

        # If still empty (e.g. specific niche model not in current dealer inventory), provide direct dealership search card
        if not results:
            results.append(
                StoreResult(
                    id=f"proleasing_{abs(hash(clean_query)) % 100000}",
                    store_name="Proleasing Motors",
                    store_icon="car",
                    country_code="RO",
                    title=f"Caută '{clean_query}' în Stocul Certificat Proleasing Motors (BMW / Ford / Rulate)",
                    price=0.0,
                    currency="EUR",
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text="Garanție 24 Luni • Verificare 360°",
                    product_url=f"https://www.rulate-proleasing.ro/auto-rulate/?s={encoded}",
                    image_url="https://images.unsplash.com/photo-1555215695-3004980ad54e?w=500&auto=format&fit=crop&q=80",
                    delivery_info="Showroom Bucov Plaza / Ploiești / București (Trade-in & Leasing)",
                    category=ProductCategory.AUTOMOTIVE,
                    store_branch="Proleasing Motors Ploiești / Bucov",
                    store_address="Str. Tineretului Nr. 4, Bucov, Prahova",
                    latitude=44.9723,
                    longitude=26.0821,
                    distance_km=None
                )
            )

        return results

    def _parse_autovit_dealer_html(self, html: str, query: str) -> List[StoreResult]:
        items: List[StoreResult] = []
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article[data-testid='listing-ad']")

        for idx, art in enumerate(articles[:10]):
            title_el = art.select_one("h2, h1, a[href*='/anunt/']")
            if not title_el:
                continue
            title = title_el.text.strip()

            # Price
            price_el = art.select_one("span.ooa-1bv8k68, h3, [data-testid='ad-price']") or art.select_one("span")
            price = 0.0
            if price_el:
                clean = re.sub(r"[^\d]", "", price_el.text)
                try:
                    price = float(clean)
                except ValueError:
                    price = 0.0

            link_el = art.select_one("a[href]")
            prod_url = link_el["href"] if link_el else "https://proleasing.autovit.ro/"

            img_el = art.select_one("img")
            img_url = img_el.get("src") or img_el.get("data-src") if img_el else None

            # Attributes (Year, Mileage, Fuel)
            text_block = art.text
            year = None
            mileage = None
            fuel = None
            trans = "Automata"

            y_match = re.search(r"\b(201[5-9]|202[0-6])\b", text_block)
            if y_match:
                year = int(y_match.group(1))

            km_match = re.search(r"(\d{1,3}(?:\.\d{3})*|\d+)\s*km", text_block, re.I)
            if km_match:
                try:
                    mileage = int(re.sub(r"[^\d]", "", km_match.group(1)))
                except ValueError:
                    mileage = None

            if "diesel" in text_block.lower():
                fuel = "Diesel"
            elif "benzina" in text_block.lower() or "benzină" in text_block.lower():
                fuel = "Benzină"
            elif "hibrid" in text_block.lower() or "hybrid" in text_block.lower():
                fuel = "Hibrid"
            elif "electric" in text_block.lower():
                fuel = "Electric"

            if "manuala" in text_block.lower() or "manuală" in text_block.lower():
                trans = "Manuală"

            items.append(
                StoreResult(
                    id=f"prol_{idx}_{abs(hash(prod_url)) % 100000}",
                    store_name="Proleasing Motors",
                    store_icon="car",
                    country_code="RO",
                    title=title,
                    price=price,
                    currency="EUR",
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text="Verificat Proleasing (Garanție)",
                    product_url=prod_url,
                    image_url=img_url or "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=500&auto=format&fit=crop&q=80",
                    delivery_info="Showroom Proleasing Bucov / Ploiești",
                    category=ProductCategory.AUTOMOTIVE,
                    store_branch="Proleasing Motors Ploiești / Bucov",
                    store_address="Str. Tineretului Nr. 4, Bucov, Prahova",
                    latitude=44.9723,
                    longitude=26.0821,
                    year=year,
                    mileage_km=mileage,
                    fuel_type=fuel,
                    transmission=trans
                )
            )

        return items

    def _parse_rulate_portal_html(self, html: str, query: str) -> List[StoreResult]:
        items: List[StoreResult] = []
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".car-item, .vehicle-card, .listing-card, article")

        for idx, card in enumerate(cards[:10]):
            title_el = card.select_one("h2, h3, .title, a[href*='/auto/']")
            if not title_el:
                continue
            title = title_el.text.strip()
            if len(title) < 4:
                continue

            price_el = card.select_one(".price, .pret, span[class*='price']")
            price = 0.0
            if price_el:
                clean = re.sub(r"[^\d]", "", price_el.text)
                try:
                    price = float(clean)
                except ValueError:
                    price = 0.0

            link_el = card.select_one("a[href]")
            prod_url = "https://www.rulate-proleasing.ro/auto-rulate/"
            if link_el and link_el.get("href"):
                h = link_el["href"]
                prod_url = ("https://www.rulate-proleasing.ro" + h) if h.startswith("/") else h

            img_el = card.select_one("img")
            img_url = img_el.get("src") or img_el.get("data-src") if img_el else None

            # Specs
            card_text = card.text
            y_match = re.search(r"\b(201[5-9]|202[0-6])\b", card_text)
            year = int(y_match.group(1)) if y_match else None

            km_match = re.search(r"(\d{1,3}(?:\.\d{3})*|\d+)\s*km", card_text, re.I)
            mileage = int(re.sub(r"[^\d]", "", km_match.group(1))) if km_match else None

            fuel = "Diesel" if "diesel" in card_text.lower() else ("Benzină" if "benzin" in card_text.lower() else "Hibrid")

            items.append(
                StoreResult(
                    id=f"prol_cat_{idx}_{abs(hash(prod_url)) % 100000}",
                    store_name="Proleasing Motors",
                    store_icon="car",
                    country_code="RO",
                    title=title,
                    price=price,
                    currency="EUR",
                    in_stock=True,
                    stock_level=StockLevel.IN_STOCK,
                    stock_badge_text="Certificat Proleasing (Istoric Real)",
                    product_url=prod_url,
                    image_url=img_url or "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=500&auto=format&fit=crop&q=80",
                    delivery_info="Showroom Proleasing Motors (Livrare Imediată)",
                    category=ProductCategory.AUTOMOTIVE,
                    store_branch="Proleasing Motors Ploiești / Bucov",
                    store_address="Str. Tineretului Nr. 4, Bucov, Prahova",
                    latitude=44.9723,
                    longitude=26.0821,
                    year=year,
                    mileage_km=mileage,
                    fuel_type=fuel,
                    transmission="Automata"
                )
            )

        return items
