import sqlite3
import os
import time
from typing import List, Optional, Dict
from core.schema import StoreResult, StockLevel, ProductCategory

CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "storestock_cache.db")

class PersistentSearchCache:
    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Fast write-ahead logging & compact disk usage
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_products (
                    id TEXT,
                    query_key TEXT,
                    country_code TEXT,
                    store_name TEXT,
                    store_icon TEXT,
                    title TEXT,
                    price REAL,
                    currency TEXT,
                    in_stock INTEGER,
                    stock_level TEXT,
                    stock_badge_text TEXT,
                    product_url TEXT PRIMARY KEY,
                    image_url TEXT,
                    category TEXT,
                    delivery_info TEXT,
                    store_branch TEXT,
                    distance_km REAL,
                    last_updated INTEGER
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_country 
                ON cached_products(query_key, country_code);
            """)
            conn.commit()

    def get_cached_results(self, query: str, country_code: str = "RO") -> List[StoreResult]:
        """
        Retrieves matching cached products from SQLite in sub-5ms.
        """
        q_key = query.strip().lower()
        country_code = country_code.upper()
        results: List[StoreResult] = []

        try:
            with self._get_connection() as conn:
                # 1. Exact query match
                cursor = conn.execute(
                    """
                    SELECT * FROM cached_products 
                    WHERE query_key = ? AND country_code = ?
                    ORDER BY in_stock DESC, last_updated DESC
                    LIMIT 80
                    """,
                    (q_key, country_code)
                )
                rows = cursor.fetchall()

                # 2. If exact query has fewer than 6 items, search for products whose title contains the query
                if len(rows) < 6:
                    cursor = conn.execute(
                        """
                        SELECT * FROM cached_products 
                        WHERE country_code = ? AND title LIKE ?
                        ORDER BY in_stock DESC, last_updated DESC
                        LIMIT 60
                        """,
                        (country_code, f"%{q_key}%")
                    )
                    rows = cursor.fetchall()

                for row in rows:
                    results.append(
                        StoreResult(
                            id=row["id"] or f"cached_{hash(row['product_url']) % 100000}",
                            store_name=row["store_name"],
                            store_icon=row["store_icon"] or "shopping-bag",
                            country_code=row["country_code"],
                            title=row["title"],
                            price=float(row["price"] or 0.0),
                            currency=row["currency"] or "RON",
                            in_stock=bool(row["in_stock"]),
                            stock_level=StockLevel(row["stock_level"]) if row["stock_level"] in [e.value for e in StockLevel] else StockLevel.IN_STOCK,
                            stock_badge_text=row["stock_badge_text"] or ("In Stock" if row["in_stock"] else "Out of Stock"),
                            product_url=row["product_url"],
                            image_url=row["image_url"],
                            delivery_info=row["delivery_info"] or "Instant Verified Cache",
                            category=ProductCategory(row["category"]) if row["category"] in [e.value for e in ProductCategory] else ProductCategory.GENERAL,
                            store_branch=row["store_branch"],
                            distance_km=float(row["distance_km"]) if row["distance_km"] is not None else None
                        )
                    )
        except Exception as e:
            print(f"[PersistentSearchCache] Error reading cache: {e}")

        return results

    def save_results(self, query: str, country_code: str, items: List[StoreResult]):
        """
        Saves or updates products in SQLite permanently without accumulating duplicate rows.
        """
        if not items:
            return
        q_key = query.strip().lower()
        country_code = country_code.upper()
        now_ts = int(time.time())

        records = []
        for it in items:
            records.append((
                it.id,
                q_key,
                country_code,
                it.store_name,
                it.store_icon,
                it.title,
                float(it.price or 0.0),
                it.currency or "RON",
                1 if it.in_stock else 0,
                it.stock_level.value if hasattr(it.stock_level, "value") else str(it.stock_level),
                it.stock_badge_text or "",
                it.product_url,
                it.image_url or "",
                it.category.value if hasattr(it.category, "value") else str(it.category),
                it.delivery_info or "",
                it.store_branch or None,
                float(it.distance_km) if it.distance_km is not None else None,
                now_ts
            ))

        try:
            with self._get_connection() as conn:
                conn.executemany(
                    """
                    INSERT INTO cached_products (
                        id, query_key, country_code, store_name, store_icon,
                        title, price, currency, in_stock, stock_level,
                        stock_badge_text, product_url, image_url, category,
                        delivery_info, store_branch, distance_km, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(product_url) DO UPDATE SET
                        price = excluded.price,
                        in_stock = excluded.in_stock,
                        stock_level = excluded.stock_level,
                        stock_badge_text = excluded.stock_badge_text,
                        image_url = CASE WHEN excluded.image_url != '' THEN excluded.image_url ELSE cached_products.image_url END,
                        store_branch = excluded.store_branch,
                        distance_km = excluded.distance_km,
                        last_updated = excluded.last_updated;
                    """,
                    records
                )
                conn.commit()
        except Exception as e:
            print(f"[PersistentSearchCache] Error saving cache: {e}")
