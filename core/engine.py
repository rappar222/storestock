import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, AsyncGenerator, Optional
from core.schema import StoreResult, SearchResponse, StockLevel
from core.countries import COUNTRIES_REGISTRY
from core.relevance import calculate_relevance
from core.branches import attach_branch_info
from core.alerts import AlertManager
from core.ai_intent import analyze_user_intent, score_with_ai_intent
from providers.base import BaseProvider
from providers.ro.emag import EmagProvider
from providers.ro.altex import AltexProvider
from providers.ro.mediagalaxy import MediaGalaxyProvider
from providers.ro.pcgarage import PCGarageProvider
from providers.ro.flanco import FlancoProvider
from providers.ro.auchan import AuchanProvider
from providers.ro.evomag import EvoMagProvider
from providers.global_platforms.amazon import AmazonProvider
from providers.global_platforms.aliexpress import AliExpressProvider
from providers.global_platforms.temu import TemuProvider
from providers.global_platforms.alibaba import AlibabaProvider
from providers.us.microcenter import MicroCenterProvider
from providers.us.bestbuy import BestBuyProvider
from providers.us.walmart import WalmartProvider
from providers.au.scorptec import ScorptecProvider
from providers.au.jbhifi import JBHiFiProvider
from providers.cars.auto_market import AutoMarketProvider
from providers.ro.proleasing import ProleasingProvider

# International Country Flagship Retailers
from providers.de.mediamarkt import MediaMarktDEProvider
from providers.de.mindfactory import MindfactoryDEProvider
from providers.gb.currys import CurrysUKProvider
from providers.gb.scan import ScanUKProvider
from providers.fr.fnac import FnacFRProvider
from providers.fr.ldlc import LDLCFRProvider
from providers.it.mediaworld import MediaWorldITProvider
from providers.it.unieuro import UnieuroITProvider
from providers.es.pccomponentes import PcComponentesESProvider
from providers.es.mediamarkt_es import MediaMarktESProvider
from providers.ca.canadacomputers import CanadaComputersProvider
from providers.ca.memoryexpress import MemoryExpressCAProvider
from providers.pl.xkom import XKomPLProvider
from providers.pl.mediaexpert import MediaExpertPLProvider
from providers.nl.coolblue import CoolblueNLProvider
from providers.nl.megekko import MegekkoNLProvider
from providers.se.webhallen import WebhallenSEProvider
from providers.se.inet import InetSEProvider
from providers.ch.digitec import DigitecCHProvider
from providers.at.cyberport_at import CyberportATProvider
from providers.be.alternate_be import AlternateBEProvider
from providers.no.komplett_no import KomplettNOProvider
from providers.dk.proshop_dk import ProshopDKProvider
from providers.fi.verkkokauppa import VerkkokauppaFIProvider
from providers.cz.alza_cz import AlzaCZProvider
from providers.hu.alza_hu import AlzaHUProvider
from providers.gr.plaisio import PlaisioGRProvider
from providers.pt.worten import WortenPTProvider
from providers.ie.currys_ie import CurrysIEProvider
from providers.jp.yodobashi import YodobashiJPProvider

class SearchEngine:
    def __init__(self):
        self.alert_manager = AlertManager()

        self.providers: Dict[str, List[BaseProvider]] = {
            "RO": [
                EmagProvider(),
                AltexProvider(),
                MediaGalaxyProvider(),
                PCGarageProvider(),
                FlancoProvider(),
                EvoMagProvider(),
                AuchanProvider(),
                AmazonProvider("RO"),
                AliExpressProvider("RO"),
                TemuProvider("RO"),
                AlibabaProvider("RO"),
                AutoMarketProvider("RO"),
                ProleasingProvider()
            ],
            "US": [
                MicroCenterProvider(),
                BestBuyProvider(),
                WalmartProvider(),
                AmazonProvider("US"),
                AliExpressProvider("US"),
                TemuProvider("US"),
                AlibabaProvider("US"),
                AutoMarketProvider("US")
            ],
            "AU": [
                ScorptecProvider(),
                JBHiFiProvider(),
                AmazonProvider("AU"),
                AliExpressProvider("AU"),
                TemuProvider("AU"),
                AlibabaProvider("AU"),
                AutoMarketProvider("AU")
            ],
            "DE": [
                MediaMarktDEProvider(),
                MindfactoryDEProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("DE"),
                TemuProvider("DE"),
                AlibabaProvider("DE"),
                AutoMarketProvider("DE")
            ],
            "GB": [
                CurrysUKProvider(),
                ScanUKProvider(),
                AmazonProvider("GB"),
                AliExpressProvider("GB"),
                TemuProvider("GB"),
                AlibabaProvider("GB"),
                AutoMarketProvider("GB")
            ],
            "FR": [
                FnacFRProvider(),
                LDLCFRProvider(),
                AmazonProvider("FR"),
                AliExpressProvider("FR"),
                TemuProvider("FR"),
                AlibabaProvider("FR"),
                AutoMarketProvider("FR")
            ],
            "IT": [
                MediaWorldITProvider(),
                UnieuroITProvider(),
                AmazonProvider("IT"),
                AliExpressProvider("IT"),
                TemuProvider("IT"),
                AlibabaProvider("IT"),
                AutoMarketProvider("IT")
            ],
            "ES": [
                PcComponentesESProvider(),
                MediaMarktESProvider(),
                AmazonProvider("ES"),
                AliExpressProvider("ES"),
                TemuProvider("ES"),
                AlibabaProvider("ES"),
                AutoMarketProvider("ES")
            ],
            "CA": [
                CanadaComputersProvider(),
                MemoryExpressCAProvider(),
                AmazonProvider("CA"),
                AliExpressProvider("CA"),
                TemuProvider("CA"),
                AlibabaProvider("CA"),
                AutoMarketProvider("CA")
            ],
            "PL": [
                XKomPLProvider(),
                MediaExpertPLProvider(),
                AmazonProvider("PL"),
                AliExpressProvider("PL"),
                TemuProvider("PL"),
                AlibabaProvider("PL"),
                AutoMarketProvider("PL")
            ],
            "NL": [
                CoolblueNLProvider(),
                MegekkoNLProvider(),
                AmazonProvider("NL"),
                AliExpressProvider("NL"),
                TemuProvider("NL"),
                AlibabaProvider("NL"),
                AutoMarketProvider("NL")
            ],
            "SE": [
                WebhallenSEProvider(),
                InetSEProvider(),
                AmazonProvider("SE"),
                AliExpressProvider("SE"),
                TemuProvider("SE"),
                AlibabaProvider("SE"),
                AutoMarketProvider("SE")
            ],
            "CH": [
                DigitecCHProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("CH"),
                TemuProvider("CH"),
                AlibabaProvider("CH"),
                AutoMarketProvider("CH")
            ],
            "AT": [
                CyberportATProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("AT"),
                TemuProvider("AT"),
                AlibabaProvider("AT"),
                AutoMarketProvider("AT")
            ],
            "BE": [
                AlternateBEProvider(),
                AmazonProvider("NL"),
                AliExpressProvider("BE"),
                TemuProvider("BE"),
                AlibabaProvider("BE"),
                AutoMarketProvider("BE")
            ],
            "NO": [
                KomplettNOProvider(),
                AmazonProvider("SE"),
                AliExpressProvider("NO"),
                TemuProvider("NO"),
                AlibabaProvider("NO"),
                AutoMarketProvider("NO")
            ],
            "DK": [
                ProshopDKProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("DK"),
                TemuProvider("DK"),
                AlibabaProvider("DK"),
                AutoMarketProvider("DK")
            ],
            "FI": [
                VerkkokauppaFIProvider(),
                AmazonProvider("SE"),
                AliExpressProvider("FI"),
                TemuProvider("FI"),
                AlibabaProvider("FI"),
                AutoMarketProvider("FI")
            ],
            "CZ": [
                AlzaCZProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("CZ"),
                TemuProvider("CZ"),
                AlibabaProvider("CZ"),
                AutoMarketProvider("CZ")
            ],
            "HU": [
                AlzaHUProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("HU"),
                TemuProvider("HU"),
                AlibabaProvider("HU"),
                AutoMarketProvider("HU")
            ],
            "GR": [
                PlaisioGRProvider(),
                AmazonProvider("DE"),
                AliExpressProvider("GR"),
                TemuProvider("GR"),
                AlibabaProvider("GR"),
                AutoMarketProvider("GR")
            ],
            "PT": [
                WortenPTProvider(),
                AmazonProvider("ES"),
                AliExpressProvider("PT"),
                TemuProvider("PT"),
                AlibabaProvider("PT"),
                AutoMarketProvider("PT")
            ],
            "IE": [
                CurrysIEProvider(),
                AmazonProvider("GB"),
                AliExpressProvider("IE"),
                TemuProvider("IE"),
                AlibabaProvider("IE"),
                AutoMarketProvider("IE")
            ],
            "JP": [
                YodobashiJPProvider(),
                AmazonProvider("JP"),
                AliExpressProvider("JP"),
                TemuProvider("JP"),
                AlibabaProvider("JP"),
                AutoMarketProvider("JP")
            ]
        }
        self._cache: Dict[str, tuple[float, List[StoreResult], Dict]] = {}
        self.cache_ttl = 300

    def get_providers_for_country(self, country_code: str) -> List[BaseProvider]:
        code = country_code.upper()
        if code in self.providers:
            return self.providers[code]
        return [
            AmazonProvider(code),
            AliExpressProvider(code),
            TemuProvider(code),
            AlibabaProvider(code),
            AutoMarketProvider(code)
        ]

    def get_providers_for_query(self, query: str, country_code: str) -> List[BaseProvider]:
        code = country_code.upper()
        all_for_country = self.providers.get(code, [])
        if not all_for_country:
            return self.get_providers_for_country(code)

        ai_intent = analyze_user_intent(query)
        detected = ai_intent.get("detected_intent", "GENERAL")
        q_lower = query.lower()

        # If car / automotive query
        if detected == "VEHICLE":
            return [
                p for p in all_for_country
                if p.category == ProductCategory.AUTOMOTIVE
                or "auto" in p.store_id.lower()
                or "proleasing" in p.store_id.lower()
            ]

        # If grocery / food / dairy query
        if detected.startswith("GROCERIES") or any(
            g in q_lower for g in [
                "lapte", "milk", "paine", "bread", "unt", "butter", "oua", "eggs",
                "cafea", "coffee", "branza", "cheese", "cascaval", "faina", "zahar",
                "ulei", "carne", "pui", "bere", "vin", "apa", "iaurt", "smantana"
            ]
        ):
            grocery_providers = [
                p for p in all_for_country
                if (p.category in [ProductCategory.GROCERIES, ProductCategory.GENERAL]
                    or "auchan" in p.store_id.lower()
                    or "emag" in p.store_id.lower()
                    or "amazon" in p.store_id.lower())
                and not any(x in p.store_id.lower() for x in ["pcgarage", "flanco", "altex", "mediagalaxy", "evomag", "auto", "proleasing"])
            ]
            return grocery_providers if grocery_providers else [p for p in all_for_country if "auchan" in p.store_id.lower() or "emag" in p.store_id.lower()]

        # If tech / hardware / gaming / electronics
        is_tech = detected in ["STANDALONE_GPU", "TECH_HARDWARE"] or any(
            t in q_lower for t in [
                "rtx", "gtx", "gpu", "cpu", "intel", "amd", "ryzen", "nvidia", "a6000",
                "laptop", "macbook", "iphone", "samsung", "ps5", "playstation", "xbox",
                "switch", "nintendo", "pc", "monitor", "placa video", "procesor", "ram", "ssd",
                "tastatura", "mouse", "casti", "televizor", "oled", "tv", "asus", "gigabyte", "msi"
            ]
        )
        if is_tech:
            # Query top tech specialists + flagship marketplace
            tech_providers = [
                p for p in all_for_country
                if p.category in [ProductCategory.TECH_HARDWARE, ProductCategory.GENERAL]
                and not any(x in p.store_id.lower() for x in ["auto", "proleasing", "dedeman", "hornbach", "leroy", "mega", "freshful", "sezamo", "kaufland", "bringo"])
            ]
            return tech_providers if tech_providers else all_for_country[:6]

        # Default general query: prioritize top 6 general & specialized platforms
        return all_for_country[:6]

    async def search_all(
        self,
        query: str,
        country_code: str = "RO",
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None
    ) -> SearchResponse:
        start_time = time.time()
        country_code = country_code.upper()
        cache_key = f"{country_code}:{query.strip().lower()}"

        ai_intent = analyze_user_intent(query)

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_results, cached_intent = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                in_stock = sum(1 for r in cached_results if r.in_stock)
                return SearchResponse(
                    query=query,
                    country_code=country_code,
                    total_results=len(cached_results),
                    in_stock_count=in_stock,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    stores_searched=[p.store_name for p in self.get_providers_for_query(query, country_code)],
                    ai_intent=cached_intent,
                    results=cached_results
                )

        providers = self.get_providers_for_query(query, country_code)
        
        # Determine queries: primary query + top AI synonym if applicable
        synonyms = ai_intent.get("synonyms", [])
        alt_query = synonyms[0] if synonyms and synonyms[0].lower() != query.lower().strip() else None
        local_query = ai_intent.get("local_query")

        STORE_TIMEOUT_SECONDS = 8.0

        async def query_provider(p: BaseProvider):
            # Use local language query for domestic stores (e.g. 'lapte' for RO stores when user searches 'milk')
            target_query = local_query if (local_query and p.country_code == country_code) else query
            fallback_query = query if target_query != query else alt_query
            try:
                res = await asyncio.wait_for(p.search(target_query), timeout=STORE_TIMEOUT_SECONDS)
                if fallback_query and len(res) < 3:
                    try:
                        res_alt = await asyncio.wait_for(p.search(fallback_query), timeout=STORE_TIMEOUT_SECONDS * 0.75)
                        urls = {x.product_url for x in res}
                        for it in res_alt:
                            if it.product_url not in urls:
                                res.append(it)
                                urls.add(it.product_url)
                    except Exception:
                        pass
                return res
            except Exception as e:
                print(f"[SearchEngine] Store '{p.store_name}' error: {e}")
                return []

        tasks = [asyncio.create_task(query_provider(p)) for p in providers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: List[StoreResult] = []
        stores_searched: List[str] = []
        seen_urls = set()

        for p, resp in zip(providers, responses):
            stores_searched.append(p.store_name)
            if isinstance(resp, list):
                for idx, item in enumerate(resp):
                    if item.product_url in seen_urls:
                        continue
                    seen_urls.add(item.product_url)

                    branch_info = attach_branch_info(item.store_name, idx, user_lat, user_lon)
                    if branch_info:
                        item.store_branch = branch_info.get("store_branch")
                        item.store_address = branch_info.get("store_address")
                        item.latitude = branch_info.get("latitude")
                        item.longitude = branch_info.get("longitude")
                        item.distance_km = branch_info.get("distance_km")

                    if item.in_stock:
                        for alert in self.alert_manager.get_all_alerts():
                            if not alert.is_triggered and alert.query.lower() in item.title.lower():
                                self.alert_manager.mark_triggered(alert.id, item.price)

                    all_results.append(item)
            elif isinstance(resp, Exception):
                print(f"[SearchEngine] Error from {p.store_name}: {resp}")

        # AI Intent-Powered Smart Ranking
        all_results.sort(
            key=lambda item: score_with_ai_intent(query, item.title, item.price, item.in_stock, intent_info=ai_intent),
            reverse=True
        )

        # Cache results
        self._cache[cache_key] = (time.time(), all_results, ai_intent)

        in_stock_count = sum(1 for r in all_results if r.in_stock)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return SearchResponse(
            query=query,
            country_code=country_code,
            total_results=len(all_results),
            in_stock_count=in_stock_count,
            execution_time_ms=elapsed_ms,
            stores_searched=stores_searched,
            ai_intent=ai_intent,
            results=all_results
        )

    async def stream_search(
        self,
        query: str,
        country_code: str = "RO",
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None
    ) -> AsyncGenerator[Dict, None]:
        country_code = country_code.upper()
        ai_intent = analyze_user_intent(query, country_code)
        providers = self.get_providers_for_query(query, country_code)

        # First yield the AI Intent detection payload to the UI
        yield {
            "type": "ai_intent",
            "payload": ai_intent
        }

        # 1. High-speed cache check (< 1ms)
        cache_key = f"{country_code}:{query.lower().strip()}"
        if cache_key in self._cache:
            cached_time, cached_results, cached_intent = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                store_items: Dict[str, list] = {}
                for it in cached_results:
                    store_items.setdefault(it.store_name, []).append(it)

                for store_name, items in store_items.items():
                    yield {
                        "type": "provider_result",
                        "payload": {
                            "store_name": store_name,
                            "store_icon": items[0].store_icon if items else "shopping-bag",
                            "elapsed_ms": 0.5,
                            "items": [r.model_dump() for r in items]
                        }
                    }
                return

        synonyms = ai_intent.get("synonyms", [])
        alt_query = synonyms[0] if synonyms and synonyms[0].lower() != query.lower().strip() else None
        local_query = ai_intent.get("local_query")

        STORE_STREAM_TIMEOUT = 8.0

        async def run_provider(provider: BaseProvider):
            start_p = time.time()
            target_query = local_query if (local_query and provider.country_code == country_code) else query
            fallback_query = query if target_query != query else alt_query
            try:
                res = await asyncio.wait_for(provider.search(target_query), timeout=STORE_STREAM_TIMEOUT)
                if fallback_query and len(res) < 3:
                    try:
                        res_alt = await asyncio.wait_for(provider.search(fallback_query), timeout=STORE_STREAM_TIMEOUT * 0.75)
                        urls = {x.product_url for x in res}
                        for it in res_alt:
                            if it.product_url not in urls:
                                res.append(it)
                                urls.add(it.product_url)
                    except Exception:
                        pass

                # Attach physical store branch coordinates & distance
                for idx, item in enumerate(res):
                    branch_info = attach_branch_info(item.store_name, idx, user_lat, user_lon)
                    if branch_info:
                        item.store_branch = branch_info.get("store_branch")
                        item.store_address = branch_info.get("store_address")
                        item.latitude = branch_info.get("latitude")
                        item.longitude = branch_info.get("longitude")
                        item.distance_km = branch_info.get("distance_km")

                return {
                    "store_name": provider.store_name,
                    "store_icon": provider.store_icon,
                    "elapsed_ms": round((time.time() - start_p) * 1000, 1),
                    "items": [r.model_dump() for r in res]
                }
            except Exception as e:
                return {
                    "store_name": provider.store_name,
                    "store_icon": provider.store_icon,
                    "elapsed_ms": round((time.time() - start_p) * 1000, 1),
                    "error": str(e),
                    "items": []
                }

        tasks = [asyncio.create_task(run_provider(p)) for p in providers]
        cached_items_to_save: List[StoreResult] = []

        for coro in asyncio.as_completed(tasks):
            try:
                res = await coro
                if res and (res.get("items") or res.get("error")):
                    yield {
                        "type": "provider_result",
                        "payload": res
                    }
                    if res.get("items"):
                        for it_data in res["items"]:
                            try:
                                cached_items_to_save.append(StoreResult(**it_data))
                            except Exception:
                                pass
            except Exception:
                pass

        # Cache results in memory
        if cached_items_to_save:
            self._cache[cache_key] = (time.time(), cached_items_to_save, ai_intent)
