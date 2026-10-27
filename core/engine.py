import time
import asyncio
from typing import List, Dict, AsyncGenerator
from core.schema import StoreResult, SearchResponse, StockLevel
from core.countries import COUNTRIES_REGISTRY
from core.relevance import calculate_relevance
from providers.base import BaseProvider
from providers.ro.emag import EmagProvider
from providers.ro.altex import AltexProvider
from providers.ro.mediagalaxy import MediaGalaxyProvider
from providers.ro.pcgarage import PCGarageProvider
from providers.ro.flanco import FlancoProvider
from providers.ro.auchan import AuchanProvider
from providers.global_platforms.amazon import AmazonProvider

class SearchEngine:
    def __init__(self):
        # Register country providers
        self.providers: Dict[str, List[BaseProvider]] = {
            "RO": [
                EmagProvider(),
                AltexProvider(),
                MediaGalaxyProvider(),
                PCGarageProvider(),
                FlancoProvider(),
                AuchanProvider(),
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
        # In-memory cache: (country, query) -> (timestamp, List[StoreResult])
        self._cache: Dict[str, tuple[float, List[StoreResult]]] = {}
        self.cache_ttl = 300  # 5 minutes

    def get_providers_for_country(self, country_code: str) -> List[BaseProvider]:
        code = country_code.upper()
        if code in self.providers:
            return self.providers[code]
        # Fallback to global provider for other top countries
        return [AmazonProvider(code)]

    async def search_all(self, query: str, country_code: str = "RO") -> SearchResponse:
        start_time = time.time()
        country_code = country_code.upper()
        cache_key = f"{country_code}:{query.strip().lower()}"

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_results = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                in_stock = sum(1 for r in cached_results if r.in_stock)
                return SearchResponse(
                    query=query,
                    country_code=country_code,
                    total_results=len(cached_results),
                    in_stock_count=in_stock,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    stores_searched=[p.store_name for p in self.get_providers_for_country(country_code)],
                    results=cached_results
                )

        providers = self.get_providers_for_country(country_code)
        
        # Parallel asynchronous fan-out
        tasks = [p.search(query) for p in providers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: List[StoreResult] = []
        stores_searched: List[str] = []

        for p, resp in zip(providers, responses):
            stores_searched.append(p.store_name)
            if isinstance(resp, list):
                all_results.extend(resp)
            elif isinstance(resp, Exception):
                print(f"[SearchEngine] Error from {p.store_name}: {resp}")

        # Smart sorting: Relevance first (penalizing accessories like stands/cables), then in-stock
        all_results.sort(
            key=lambda item: calculate_relevance(query, item.title, item.price, item.in_stock),
            reverse=True
        )

        # Cache results
        self._cache[cache_key] = (time.time(), all_results)

        in_stock_count = sum(1 for r in all_results if r.in_stock)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return SearchResponse(
            query=query,
            country_code=country_code,
            total_results=len(all_results),
            in_stock_count=in_stock_count,
            execution_time_ms=elapsed_ms,
            stores_searched=stores_searched,
            results=all_results
        )

    async def stream_search(self, query: str, country_code: str = "RO") -> AsyncGenerator[Dict, None]:
        """
        Stream results store by store as soon as each provider completes.
        """
        country_code = country_code.upper()
        providers = self.get_providers_for_country(country_code)

        async def run_provider(provider: BaseProvider):
            try:
                start_p = time.time()
                res = await provider.search(query)
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
            yield provider_result
