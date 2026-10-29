import os
from typing import Dict, Type, Optional
from core.db.base import BaseDatabaseAdapter
from core.db.sqlite_adapter import SQLiteDatabaseAdapter

# Registry mapping database engine identifiers to Adapter Classes
ADAPTER_REGISTRY: Dict[str, Type[BaseDatabaseAdapter]] = {
    "sqlite": SQLiteDatabaseAdapter,
    "sqlite3": SQLiteDatabaseAdapter,
}

# Try registering Postgres adapter
try:
    from core.db.postgres_adapter import PostgresDatabaseAdapter
    ADAPTER_REGISTRY["postgres"] = PostgresDatabaseAdapter
    ADAPTER_REGISTRY["postgresql"] = PostgresDatabaseAdapter
except Exception:
    pass

_GLOBAL_DB_ADAPTER: Optional[BaseDatabaseAdapter] = None

def register_adapter(engine_name: str, adapter_cls: Type[BaseDatabaseAdapter]) -> None:
    """Dynamically register a new database adapter (e.g. MySQL, Redis, MongoDB)."""
    ADAPTER_REGISTRY[engine_name.lower().strip()] = adapter_cls

def init_database(db_type: Optional[str] = None, connection_string: Optional[str] = None) -> BaseDatabaseAdapter:
    """
    Initializes and returns a configured BaseDatabaseAdapter instance.
    Detection order:
    1. Explicit arguments passed to init_database
    2. STORESTOCK_DB_TYPE environment variable ('sqlite', 'postgres', etc.)
    3. DATABASE_URL / POSTGRES_URL environment variables
    4. Default: SQLite on disk at data/storestock_cache.db
    """
    global _GLOBAL_DB_ADAPTER

    db_url = connection_string or os.environ.get("DATABASE_URL") or os.environ.get("STORESTOCK_DATABASE_URL")
    engine = (db_type or os.environ.get("STORESTOCK_DB_TYPE", "")).lower().strip()

    if not engine and db_url:
        if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
            engine = "postgres"
        elif db_url.startswith("sqlite://"):
            engine = "sqlite"

    if not engine:
        engine = "sqlite"

    adapter_cls = ADAPTER_REGISTRY.get(engine)
    if not adapter_cls:
        raise ValueError(
            f"Unsupported database engine '{engine}'. "
            f"Supported engines: {list(ADAPTER_REGISTRY.keys())}. "
            f"Use register_adapter() to add custom database implementations."
        )

    if engine == "sqlite":
        # Extract path if sqlite:///path/to/db
        sqlite_path = None
        if db_url and db_url.startswith("sqlite:///"):
            sqlite_path = db_url.replace("sqlite:///", "")
        elif db_url and db_url.startswith("sqlite://"):
            sqlite_path = db_url.replace("sqlite://", "")
        
        adapter = adapter_cls(db_path=sqlite_path) if sqlite_path else adapter_cls()
    else:
        adapter = adapter_cls(connection_url=db_url) if db_url else adapter_cls()

    _GLOBAL_DB_ADAPTER = adapter
    return adapter

def get_database_adapter() -> BaseDatabaseAdapter:
    """Returns the shared global database adapter instance (lazy initialization)."""
    global _GLOBAL_DB_ADAPTER
    if _GLOBAL_DB_ADAPTER is None:
        _GLOBAL_DB_ADAPTER = init_database()
    return _GLOBAL_DB_ADAPTER
