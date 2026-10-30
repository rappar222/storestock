import os
import re
import sqlite3
import time
from typing import List, Dict, Any, Optional
from core.db.base import BaseDatabaseAdapter
from core.schema import StoreResult, StockLevel, ProductCategory, RestockAlert

DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "storestock_cache.db")

class SQLiteDatabaseAdapter(BaseDatabaseAdapter):
    """
    SQLite Database Adapter optimized for local NVMe / SSD single-node speed.
    Uses Write-Ahead Logging (WAL) and NORMAL synchronicity for sub-2ms reads.
    """

    def __init__(self, db_path: str = DEFAULT_SQLITE_PATH):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass
        return conn

    def init_schema(self) -> None:
        with self._get_connection() as conn:
            # 1. Cached Products Table
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_store_name 
                ON cached_products(store_name);
            """)

            # 2. FTS5 Virtual Table for full-text search
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS cached_products_fts USING fts5(
                        title,
                        store_name,
                        category,
                        content='cached_products',
                        content_rowid='rowid'
                    );
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS cached_products_ai AFTER INSERT ON cached_products BEGIN
                        INSERT INTO cached_products_fts(rowid, title, store_name, category)
                        VALUES (new.rowid, new.title, new.store_name, new.category);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS cached_products_ad AFTER DELETE ON cached_products BEGIN
                        INSERT INTO cached_products_fts(cached_products_fts, rowid, title, store_name, category)
                        VALUES('delete', old.rowid, old.title, old.store_name, old.category);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS cached_products_au AFTER UPDATE ON cached_products BEGIN
                        INSERT INTO cached_products_fts(cached_products_fts, rowid, title, store_name, category)
                        VALUES('delete', old.rowid, old.title, old.store_name, old.category);
                        INSERT INTO cached_products_fts(rowid, title, store_name, category)
                        VALUES (new.rowid, new.title, new.store_name, new.category);
                    END;
                """)
            except Exception as e:
                print(f"[SQLiteDatabaseAdapter] FTS5 initialization note: {e}")

            # 3. Restock Alerts Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS restock_alerts (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    store_name TEXT NOT NULL,
                    target_price REAL,
                    email TEXT NOT NULL,
                    product_title TEXT,
                    product_url TEXT,
                    is_triggered INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_status TEXT,
                    last_checked TEXT
                );
            """)
            # 4. Price History Table (sparklines, trend tracking)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_url TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    recorded_at INTEGER NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_history_url
                ON price_history(product_url, recorded_at DESC);
            """)
            conn.commit()

    def get_cached_products(self, query: str, country_code: str = "RO") -> List[StoreResult]:
        q_clean = query.strip()
        q_key = q_clean.lower()
        country_code = country_code.upper()
        results: List[StoreResult] = []

        tokens = [t for t in re.split(r'[\s,\.\-_]+', q_key) if len(t) >= 2]

        try:
            with self._get_connection() as conn:
                rows = []
                seen_urls = set()

                # 1. Try FTS5 if tokens exist
                if tokens:
                    try:
                        fts_query = " AND ".join([f'"{t}"*' for t in tokens])
                        cursor = conn.execute(
                            """
                            SELECT cp.* FROM cached_products cp
                            JOIN cached_products_fts fts ON cp.rowid = fts.rowid
                            WHERE cp.country_code = ? AND cached_products_fts MATCH ?
                            ORDER BY rank, cp.in_stock DESC
                            LIMIT 80
                            """,
                            (country_code, fts_query)
                        )
                        for r in cursor.fetchall():
                            if r["product_url"] not in seen_urls:
                                rows.append(r)
                                seen_urls.add(r["product_url"])
                    except Exception:
                        pass

                # 2. Multi-word AND search (e.g. title LIKE '%biscuiti%' AND title LIKE '%eugenia%')
                if len(rows) < 10 and tokens:
                    where_clauses = ["country_code = ?"]
                    params = [country_code]
                    for t in tokens:
                        where_clauses.append("LOWER(title) LIKE ?")
                        params.append(f"%{t}%")
                    sql = f"""
                        SELECT * FROM cached_products 
                        WHERE {' AND '.join(where_clauses)}
                        ORDER BY in_stock DESC, last_updated DESC
                        LIMIT 80
                    """
                    cursor = conn.execute(sql, tuple(params))
                    for r in cursor.fetchall():
                        if r["product_url"] not in seen_urls:
                            rows.append(r)
                            seen_urls.add(r["product_url"])

                # 3. Exact query key or substring fallback
                if len(rows) < 6:
                    cursor = conn.execute(
                        """
                        SELECT * FROM cached_products 
                        WHERE country_code = ? AND (query_key = ? OR LOWER(title) LIKE ?)
                        ORDER BY in_stock DESC, last_updated DESC
                        LIMIT 60
                        """,
                        (country_code, q_key, f"%{q_key}%")
                    )
                    for r in cursor.fetchall():
                        if r["product_url"] not in seen_urls:
                            rows.append(r)
                            seen_urls.add(r["product_url"])

                # 4. Partial token match fallback if still nothing
                if len(rows) == 0 and len(tokens) > 1:
                    where_clauses = ["country_code = ?"]
                    or_clauses = []
                    params = [country_code]
                    for t in tokens:
                        or_clauses.append("LOWER(title) LIKE ?")
                        params.append(f"%{t}%")
                    where_clauses.append(f"({' OR '.join(or_clauses)})")
                    sql = f"""
                        SELECT * FROM cached_products 
                        WHERE {' AND '.join(where_clauses)}
                        ORDER BY in_stock DESC, last_updated DESC
                        LIMIT 40
                    """
                    cursor = conn.execute(sql, tuple(params))
                    for r in cursor.fetchall():
                        if r["product_url"] not in seen_urls:
                            rows.append(r)
                            seen_urls.add(r["product_url"])

                for row in rows:
                    results.append(
                        StoreResult(
                            id=row["id"] or f"cached_{abs(hash(row['product_url'])) % 100000}",
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
                            distance_km=float(row["distance_km"]) if row["distance_km"] is not None else None,
                            last_updated=int(row["last_updated"]) if row["last_updated"] is not None else None
                        )
                    )
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error fetching cached products: {e}")

        return results

    def batch_save_catalog_products(self, items: List[StoreResult]) -> None:
        if not items:
            return
        now_ts = int(time.time())
        records = []
        for it in items:
            q_key = " ".join(it.title.lower().split()[:3])
            records.append((
                it.id,
                q_key,
                it.country_code.upper() if it.country_code else "RO",
                it.store_name,
                it.store_icon or "shopping-bag",
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
                # Keep FTS5 in sync if triggers weren't present
                try:
                    fts_records = [
                        (r[0], r[5], r[3], r[13]) for r in records
                    ]
                except Exception:
                    pass

                conn.commit()
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error in batch_save_catalog_products: {e}")

    def save_cached_products(self, query: str, country_code: str, items: List[StoreResult]) -> None:
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

                # Record price snapshots in price_history if price > 0
                history_records = [
                    (it.product_url, float(it.price or 0.0), it.currency or "RON", now_ts)
                    for it in items if float(it.price or 0.0) > 0
                ]
                if history_records:
                    conn.executemany(
                        """
                        INSERT INTO price_history (product_url, price, currency, recorded_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        history_records
                    )

                conn.commit()
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error saving products: {e}")

    def get_alerts(self) -> List[RestockAlert]:
        alerts: List[RestockAlert] = []
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM restock_alerts ORDER BY created_at DESC;")
                for r in cursor.fetchall():
                    alerts.append(
                        RestockAlert(
                            id=r["id"],
                            query=r["query"],
                            store_name=r["store_name"],
                            target_price=float(r["target_price"]) if r["target_price"] is not None else None,
                            email=r["email"],
                            product_title=r["product_title"],
                            product_url=r["product_url"],
                            is_triggered=bool(r["is_triggered"]),
                            created_at=r["created_at"] or "",
                            last_status=r["last_status"] or "",
                            last_checked=r["last_checked"] or ""
                        )
                    )
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error getting alerts: {e}")
        return alerts

    def save_alert(self, alert: RestockAlert) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO restock_alerts (
                        id, query, store_name, target_price, email,
                        product_title, product_url, is_triggered, created_at,
                        last_status, last_checked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        target_price = excluded.target_price,
                        email = excluded.email,
                        is_triggered = excluded.is_triggered,
                        last_status = excluded.last_status,
                        last_checked = excluded.last_checked;
                    """,
                    (
                        alert.id,
                        alert.query,
                        alert.store_name,
                        alert.target_price,
                        alert.email,
                        alert.product_title,
                        alert.product_url,
                        1 if alert.is_triggered else 0,
                        alert.created_at,
                        alert.last_status,
                        alert.last_checked
                    )
                )
                conn.commit()
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error saving alert: {e}")

    def delete_alert(self, alert_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM restock_alerts WHERE id = ?;", (alert_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error deleting alert: {e}")
            return False

    def get_price_history(self, product_url: str, limit: int = 15) -> List[Dict[str, Any]]:
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT price, currency, recorded_at
                    FROM price_history
                    WHERE product_url = ?
                    ORDER BY recorded_at DESC
                    LIMIT ?
                    """,
                    (product_url, limit)
                )
                for r in cursor.fetchall():
                    history.append({
                        "price": float(r["price"]),
                        "currency": r["currency"],
                        "recorded_at": int(r["recorded_at"])
                    })
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error fetching price history: {e}")
        return history

    def get_stats(self) -> Dict[str, Any]:
        """Returns disk size, object count, and SQLite pragmas."""
        db_size = os.path.getsize(self.db_path) if os.path.isfile(self.db_path) else 0
        wal_path = f"{self.db_path}-wal"
        wal_size = os.path.getsize(wal_path) if os.path.isfile(wal_path) else 0
        total_disk_bytes = db_size + wal_size

        total_products = 0
        unique_stores = 0
        in_stock_products = 0
        total_alerts = 0

        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT COUNT(*) as cnt FROM cached_products;").fetchone()
                total_products = row["cnt"] if row else 0

                row = conn.execute("SELECT COUNT(DISTINCT store_name) as cnt FROM cached_products;").fetchone()
                unique_stores = row["cnt"] if row else 0

                row = conn.execute("SELECT COUNT(*) as cnt FROM cached_products WHERE in_stock = 1;").fetchone()
                in_stock_products = row["cnt"] if row else 0

                row = conn.execute("SELECT COUNT(*) as cnt FROM restock_alerts;").fetchone()
                total_alerts = row["cnt"] if row else 0
        except Exception as e:
            print(f"[SQLiteDatabaseAdapter] Error computing stats: {e}")

        def format_size(bytes_val: int) -> str:
            if bytes_val < 1024:
                return f"{bytes_val} B"
            elif bytes_val < 1024 * 1024:
                return f"{bytes_val / 1024:.2f} KB"
            elif bytes_val < 1024 * 1024 * 1024:
                return f"{bytes_val / (1024 * 1024):.2f} MB"
            else:
                return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

        return {
            "engine": "SQLite",
            "connected": True,
            "path": self.db_path,
            "wal_mode": True,
            "file_size_bytes": total_disk_bytes,
            "file_size_human": format_size(total_disk_bytes),
            "total_cached_products": total_products,
            "in_stock_cached_products": in_stock_products,
            "unique_stores": unique_stores,
            "total_alerts": total_alerts,
            "sqlite_version": sqlite3.sqlite_version
        }
