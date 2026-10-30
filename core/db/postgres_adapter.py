import os
import time
from typing import List, Dict, Any, Optional
from core.db.base import BaseDatabaseAdapter
from core.schema import StoreResult, StockLevel, ProductCategory, RestockAlert

class PostgresDatabaseAdapter(BaseDatabaseAdapter):
    """
    PostgreSQL Database Adapter for scaled distributed deployments
    or central TrueNAS PostgreSQL service.
    
    Can be configured via:
    - DATABASE_URL=postgresql://user:password@host:5432/storestock
    - Or individual environment variables: POSTGRES_HOST, POSTGRES_PORT, etc.
    """

    def __init__(self, connection_url: Optional[str] = None):
        self.connection_url = connection_url or os.environ.get(
            "DATABASE_URL",
            os.environ.get("POSTGRES_URL", "postgresql://storestock:storestock@localhost:5432/storestock")
        )
        self._driver = self._check_driver()
        self.init_schema()

    def _check_driver(self):
        try:
            import psycopg
            return "psycopg3"
        except ImportError:
            pass

        try:
            import psycopg2
            return "psycopg2"
        except ImportError:
            pass

        raise ImportError(
            "PostgreSQL adapter requires a Postgres client library. "
            "Please install it using: pip install psycopg[binary] or pip install psycopg2-binary"
        )

    def _get_connection(self):
        if self._driver == "psycopg3":
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(self.connection_url, row_factory=dict_row)
        else:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(self.connection_url)
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            return conn

    def init_schema(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Cached Products Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cached_products (
                        id TEXT,
                        query_key TEXT,
                        country_code TEXT,
                        store_name TEXT,
                        store_icon TEXT,
                        title TEXT,
                        price DOUBLE PRECISION,
                        currency TEXT,
                        in_stock INTEGER,
                        stock_level TEXT,
                        stock_badge_text TEXT,
                        product_url TEXT PRIMARY KEY,
                        image_url TEXT,
                        category TEXT,
                        delivery_info TEXT,
                        store_branch TEXT,
                        distance_km DOUBLE PRECISION,
                        last_updated BIGINT
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pg_query_country 
                    ON cached_products(query_key, country_code);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pg_store_name 
                    ON cached_products(store_name);
                """)

                # 2. Restock Alerts Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS restock_alerts (
                        id TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        store_name TEXT NOT NULL,
                        target_price DOUBLE PRECISION,
                        email TEXT NOT NULL,
                        product_title TEXT,
                        product_url TEXT,
                        is_triggered INTEGER DEFAULT 0,
                        created_at TEXT,
                        last_status TEXT,
                        last_checked TEXT
                    );
                """)
                # 3. Price History Table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS price_history (
                        id SERIAL PRIMARY KEY,
                        product_url TEXT NOT NULL,
                        price DOUBLE PRECISION NOT NULL,
                        currency TEXT NOT NULL,
                        recorded_at BIGINT NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pg_price_history_url
                    ON price_history(product_url, recorded_at DESC);
                """)
            conn.commit()

    def get_cached_products(self, query: str, country_code: str = "RO") -> List[StoreResult]:
        q_key = query.strip().lower()
        country_code = country_code.upper()
        results: List[StoreResult] = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM cached_products 
                        WHERE query_key = %s AND country_code = %s
                        ORDER BY in_stock DESC, last_updated DESC
                        LIMIT 80
                        """,
                        (q_key, country_code)
                    )
                    rows = cur.fetchall()

                    if len(rows) < 6:
                        cur.execute(
                            """
                            SELECT * FROM cached_products 
                            WHERE country_code = %s AND title ILIKE %s
                            ORDER BY in_stock DESC, last_updated DESC
                            LIMIT 60
                            """,
                            (country_code, f"%{q_key}%")
                        )
                        rows = cur.fetchall()

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
                                distance_km=float(row["distance_km"]) if row["distance_km"] is not None else None
                            )
                        )
        except Exception as e:
            print(f"[PostgresDatabaseAdapter] Error fetching cached products: {e}")

        return results

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
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO cached_products (
                            id, query_key, country_code, store_name, store_icon,
                            title, price, currency, in_stock, stock_level,
                            stock_badge_text, product_url, image_url, category,
                            delivery_info, store_branch, distance_km, last_updated
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(product_url) DO UPDATE SET
                            price = EXCLUDED.price,
                            in_stock = EXCLUDED.in_stock,
                            stock_level = EXCLUDED.stock_level,
                            stock_badge_text = EXCLUDED.stock_badge_text,
                            image_url = CASE WHEN EXCLUDED.image_url != '' THEN EXCLUDED.image_url ELSE cached_products.image_url END,
                            store_branch = EXCLUDED.store_branch,
                            distance_km = EXCLUDED.distance_km,
                            last_updated = EXCLUDED.last_updated;
                    """
                    cur.executemany(sql, records)

                    # Record price snapshots in price_history if price > 0
                    history_records = [
                        (it.product_url, float(it.price or 0.0), it.currency or "RON", now_ts)
                        for it in items if float(it.price or 0.0) > 0
                    ]
                    if history_records:
                        cur.executemany(
                            """
                            INSERT INTO price_history (product_url, price, currency, recorded_at)
                            VALUES (%s, %s, %s, %s)
                            """,
                            history_records
                        )
                conn.commit()
        except Exception as e:
            print(f"[PostgresDatabaseAdapter] Error saving products: {e}")

    def get_alerts(self) -> List[RestockAlert]:
        alerts: List[RestockAlert] = []
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM restock_alerts ORDER BY created_at DESC;")
                    for r in cur.fetchall():
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
            print(f"[PostgresDatabaseAdapter] Error getting alerts: {e}")
        return alerts

    def save_alert(self, alert: RestockAlert) -> None:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO restock_alerts (
                            id, query, store_name, target_price, email,
                            product_title, product_url, is_triggered, created_at,
                            last_status, last_checked
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(id) DO UPDATE SET
                            target_price = EXCLUDED.target_price,
                            email = EXCLUDED.email,
                            is_triggered = EXCLUDED.is_triggered,
                            last_status = EXCLUDED.last_status,
                            last_checked = EXCLUDED.last_checked;
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
            print(f"[PostgresDatabaseAdapter] Error saving alert: {e}")

    def delete_alert(self, alert_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM restock_alerts WHERE id = %s;", (alert_id,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            print(f"[PostgresDatabaseAdapter] Error deleting alert: {e}")
            return False

    def get_price_history(self, product_url: str, limit: int = 15) -> List[Dict[str, Any]]:
        history = []
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT price, currency, recorded_at
                        FROM price_history
                        WHERE product_url = %s
                        ORDER BY recorded_at DESC
                        LIMIT %s
                        """,
                        (product_url, limit)
                    )
                    for r in cur.fetchall():
                        history.append({
                            "price": float(r[0] if isinstance(r, (list, tuple)) else r["price"]),
                            "currency": r[1] if isinstance(r, (list, tuple)) else r["currency"],
                            "recorded_at": int(r[2] if isinstance(r, (list, tuple)) else r["recorded_at"])
                        })
        except Exception as e:
            print(f"[PostgresDatabaseAdapter] Error fetching price history: {e}")
        return history

    def get_stats(self) -> Dict[str, Any]:
        total_products = 0
        unique_stores = 0
        in_stock_products = 0
        total_alerts = 0
        db_size_bytes = 0

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_database_size(current_database());")
                    row = cur.fetchone()
                    db_size_bytes = row[0] if isinstance(row, (list, tuple)) else row.get("pg_database_size", 0)

                    cur.execute("SELECT COUNT(*) FROM cached_products;")
                    row = cur.fetchone()
                    total_products = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)

                    cur.execute("SELECT COUNT(DISTINCT store_name) FROM cached_products;")
                    row = cur.fetchone()
                    unique_stores = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)

                    cur.execute("SELECT COUNT(*) FROM cached_products WHERE in_stock = 1;")
                    row = cur.fetchone()
                    in_stock_products = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)

                    cur.execute("SELECT COUNT(*) FROM restock_alerts;")
                    row = cur.fetchone()
                    total_alerts = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)
        except Exception as e:
            print(f"[PostgresDatabaseAdapter] Error computing stats: {e}")

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
            "engine": "PostgreSQL",
            "connected": True,
            "driver": self._driver,
            "database_size_bytes": db_size_bytes,
            "database_size_human": format_size(db_size_bytes),
            "total_cached_products": total_products,
            "in_stock_cached_products": in_stock_products,
            "unique_stores": unique_stores,
            "total_alerts": total_alerts
        }
