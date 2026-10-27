import time
import asyncio
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
from providers.ro.glovo_express import GlovoExpressProvider
from providers.global_platforms.amazon import AmazonProvider

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
                GlovoExpressProvider(),
                AmazonProvider("RO")
            ],
            "US": [
                AmazonProvider("US")
            ],
            "DE": [
                AmazonProvider("DE")
            ],
            "GB": [
                AmazonProvider("GB")
            ]
        }
        self._cache: Dict[str, tuple[float, List[StoreResult], Dict]] = {}
        self.cache_ttl = 300

    def get_providers_for_country(self, country_code: str) -> List[BaseProvider]:
        code = country_code.upper()
        if code in self.providers:
            return self.providers[code]
        return [AmazonProvider(code)]

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
                    stores_searched=[p.store_name for p in self.get_providers_for_country(country_code)],
                    ai_intent=cached_intent,
                    results=cached_results
                )

        providers = self.get_providers_for_country(country_code)
        
        # Determine queries: primary query + top AI synonym if applicable
        synonyms = ai_intent.get("synonyms", [])
        alt_query = synonyms[0] if synonyms and synonyms[0].lower() != query.lower().strip() else None

        async def query_provider(p: BaseProvider):
            res = await p.search(query)
            if alt_query:
                try:
                    res_alt = await p.search(alt_query)
                    urls = {x.product_url for x in res}
                    for it in res_alt:
                        if it.product_url not in urls:
                            res.append(it)
                            urls.add(it.product_url)
                except Exception:
                    pass
            return res

        tasks = [query_provider(p) for p in providers]
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
        providers = self.get_providers_for_country(country_code)
        ai_intent = analyze_user_intent(query)

        # First yield the AI Intent detection payload to the UI
        yield {
            "type": "ai_intent",
            "payload": ai_intent
        }

        synonyms = ai_intent.get("synonyms", [])
        alt_query = synonyms[0] if synonyms and synonyms[0].lower() != query.lower().strip() else None

        async def run_provider(provider: BaseProvider):
            try:
                start_p = time.time()
                res = await provider.search(query)
                if alt_query:
                    try:
                        res_alt = await provider.search(alt_query)
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
                    "error": str(e),
                    "items": []
                }

        tasks = [asyncio.create_task(run_provider(p)) for p in providers]

        for future in asyncio.as_completed(tasks):
            provider_result = await future
            yield {
                "type": "provider_result",
                "payload": provider_result
            }
