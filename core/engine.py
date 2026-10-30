import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, AsyncGenerator, Optional
from core.schema import StoreResult, SearchResponse, StockLevel, ProductCategory
from core.countries import COUNTRIES_REGISTRY
from core.relevance import calculate_relevance
from core.branches import attach_branch_info
from core.alerts import AlertManager
from core.ai_intent import analyze_user_intent, score_with_ai_intent
from core.cache_db import PersistentSearchCache
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
        self.persistent_cache = PersistentSearchCache()

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
                if getattr(p, "category", ProductCategory.GENERAL) == ProductCategory.AUTOMOTIVE
                or "auto" in getattr(p, "store_id", "").lower()
                or "proleasing" in getattr(p, "store_id", "").lower()
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
                if (getattr(p, "category", ProductCategory.GENERAL) in [ProductCategory.GROCERIES, ProductCategory.GENERAL]
                    or "auchan" in getattr(p, "store_id", "").lower()
                    or "emag" in getattr(p, "store_id", "").lower()
                    or "amazon" in getattr(p, "store_id", "").lower())
                and not any(x in getattr(p, "store_id", "").lower() for x in ["pcgarage", "flanco", "altex", "mediagalaxy", "evomag", "auto", "proleasing"])
            ]
            return grocery_providers if grocery_providers else [p for p in all_for_country if "auchan" in getattr(p, "store_id", "").lower() or "emag" in getattr(p, "store_id", "").lower()]

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
                if getattr(p, "category", ProductCategory.GENERAL) in [ProductCategory.TECH_HARDWARE, ProductCategory.GENERAL]
                and not any(x in getattr(p, "store_id", "").lower() for x in ["auto", "proleasing", "dedeman", "hornbach", "leroy", "mega", "freshful", "sezamo", "kaufland", "bringo"])
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
        """
        Pure Local Cache Reader:
        ZERO server outbound scraper requests to protect server home IP from bot detection.
        """
        start_time = time.time()
        country_code = country_code.upper()
        ai_intent = analyze_user_intent(query, country_code)
        
        cached_disk_items = await asyncio.to_thread(self.persistent_cache.get_cached_results, query, country_code)
        in_stock_count = sum(1 for r in cached_disk_items if r.in_stock)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return SearchResponse(
            query=query,
            country_code=country_code,
            total_results=len(cached_disk_items),
            in_stock_count=in_stock_count,
            execution_time_ms=elapsed_ms,
            stores_searched=[],
            ai_intent=ai_intent,
            results=cached_disk_items
        )

    async def stream_search(
        self,
        query: str,
        country_code: str = "RO",
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        cached_only: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Pure Local Cache SSE Streamer:
        ZERO server outbound scraper requests. Returns only existing NVMe database cache.
        """
        country_code = country_code.upper()
        ai_intent = analyze_user_intent(query, country_code)

        yield {
            "type": "ai_intent",
            "payload": ai_intent
        }

        # TrueNAS Persistent Disk Cache (< 2ms)
        cached_disk_items = await asyncio.to_thread(self.persistent_cache.get_cached_results, query, country_code)
        if cached_disk_items:
            store_items: Dict[str, list] = {}
            for it in cached_disk_items:
                store_items.setdefault(it.store_name, []).append(it)

            for store_name, items in store_items.items():
                yield {
                    "type": "provider_result",
                    "payload": {
                        "store_name": store_name,
                        "store_icon": items[0].store_icon if items else "shopping-bag",
                        "elapsed_ms": 1.2,
                        "is_instant_cache": True,
                        "items": [r.model_dump() for r in items]
                    }
                }

        # Hard stop: Never make outbound scraper calls from server!
        return
