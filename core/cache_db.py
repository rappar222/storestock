import os
from typing import List, Optional, Dict, Any
from core.schema import StoreResult
from core.db import get_database_adapter, BaseDatabaseAdapter

CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "storestock_cache.db")

class PersistentSearchCache:
    """
    High-level Persistent Search Cache facade.
    Delegates all operations to the pluggable BaseDatabaseAdapter
    (SQLite, PostgreSQL, MySQL, Redis, etc.) configured via environment.
    """

    def __init__(self, db_adapter: Optional[BaseDatabaseAdapter] = None):
        self.adapter = db_adapter or get_database_adapter()

    def get_cached_results(self, query: str, country_code: str = "RO") -> List[StoreResult]:
        """
        Retrieves matching cached products in sub-5ms from the configured database.
        """
        return self.adapter.get_cached_products(query, country_code)

    def save_results(self, query: str, country_code: str, items: List[StoreResult]) -> None:
        """
        Saves or updates products permanently without accumulating duplicate rows.
        """
        self.adapter.save_cached_products(query, country_code, items)

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns real-time statistics regarding database storage, records count, and engine health.
        """
        return self.adapter.get_stats()
