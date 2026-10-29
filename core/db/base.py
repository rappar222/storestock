import abc
from typing import List, Dict, Any, Optional
from core.schema import StoreResult, RestockAlert

class BaseDatabaseAdapter(abc.ABC):
    """
    Abstract Database Adapter interface for StoreStock.
    Standardizes connections, schema initialization, caching, and alerts
    across different storage engines (SQLite, PostgreSQL, MySQL, Redis, MongoDB).
    """

    @abc.abstractmethod
    def init_schema(self) -> None:
        """Initialize required database tables, indexes, and constraints."""
        pass

    @abc.abstractmethod
    def get_cached_products(self, query: str, country_code: str = "RO") -> List[StoreResult]:
        """Retrieve cached store items for a given search query and country."""
        pass

    @abc.abstractmethod
    def save_cached_products(self, query: str, country_code: str, items: List[StoreResult]) -> None:
        """Upsert product results into the persistent cache."""
        pass

    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Return diagnostics and statistics about the database:
        - engine type (e.g. SQLite, PostgreSQL)
        - storage size (bytes and human-readable)
        - total cached products count
        - total unique stores
        - connection status
        """
        pass

    @abc.abstractmethod
    def get_alerts(self) -> List[RestockAlert]:
        """Retrieve all active restock alerts."""
        pass

    @abc.abstractmethod
    def save_alert(self, alert: RestockAlert) -> None:
        """Persist or update a restock alert."""
        pass

    @abc.abstractmethod
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert by ID."""
        pass

    def close(self) -> None:
        """Safely close open connections or connection pools."""
        pass
