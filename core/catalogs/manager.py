import os
import json
import time
import tempfile
import asyncio
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Any
from core.schema import StoreResult, ProductCategory
from core.db import get_database_adapter
from core.branches import attach_branch_info
from core.catalogs.models import FeedConfig, FeedFormat, CatalogSyncResult
from core.catalogs.parsers import stream_feed_products
from core.catalogs.seeds import DEFAULT_SEED_PRODUCTS

DEFAULT_FEEDS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "feeds.json")

DEFAULT_PRESET_FEEDS: List[Dict[str, Any]] = [
    {
        "id": "auchan_feed",
        "name": "Auchan Romania Catalog (2Performant / Direct Feed)",
        "store_name": "Auchan Hypermarket",
        "store_icon": "shopping-cart",
        "country_code": "RO",
        "category": "groceries",
        "feed_url": os.environ.get("AUCHAN_FEED_URL", "https://feeds.2performant.com/sample/auchan.csv.gz"),
        "feed_format": "csv",
        "enabled": False,
        "currency": "RON",
        "items_count": 0
    },
    {
        "id": "carrefour_feed",
        "name": "Carrefour Romania Catalog Feed",
        "store_name": "Carrefour",
        "store_icon": "shopping-cart",
        "country_code": "RO",
        "category": "groceries",
        "feed_url": os.environ.get("CARREFOUR_FEED_URL", "https://feeds.2performant.com/sample/carrefour.csv.gz"),
        "feed_format": "csv",
        "enabled": False,
        "currency": "RON",
        "items_count": 0
    },
    {
        "id": "emag_feed",
        "name": "eMAG Marketplace Feed (Profitshare / 2P)",
        "store_name": "eMAG",
        "store_icon": "shopping-bag",
        "country_code": "RO",
        "category": "general",
        "feed_url": os.environ.get("EMAG_FEED_URL", "https://feeds.profitshare.ro/sample/emag.xml.gz"),
        "feed_format": "xml",
        "enabled": False,
        "currency": "RON",
        "items_count": 0
    },
    {
        "id": "altex_feed",
        "name": "Altex Romania Catalog Feed",
        "store_name": "Altex",
        "store_icon": "cpu",
        "country_code": "RO",
        "category": "tech_hardware",
        "feed_url": os.environ.get("ALTEX_FEED_URL", "https://feeds.2performant.com/sample/altex.csv.gz"),
        "feed_format": "csv",
        "enabled": False,
        "currency": "RON",
        "items_count": 0
    }
]

class CatalogManager:
    def __init__(self, config_path: str = DEFAULT_FEEDS_PATH):
        self.config_path = os.path.abspath(config_path)
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self.feeds: Dict[str, FeedConfig] = {}
        self._load_feeds()

    def _load_feeds(self) -> None:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for item in raw_data:
                        feed = FeedConfig(**item)
                        self.feeds[feed.id] = feed
                return
            except Exception as e:
                print(f"[CatalogManager] Warning reading {self.config_path}: {e}")

        # Initialize defaults
        for item in DEFAULT_PRESET_FEEDS:
            feed = FeedConfig(**item)
            self.feeds[feed.id] = feed
        self.save_feeds()

    def save_feeds(self) -> None:
        try:
            data = [f.model_dump() for f in self.feeds.values()]
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[CatalogManager] Failed saving feeds config: {e}")

    def list_feeds(self) -> List[FeedConfig]:
        return list(self.feeds.values())

    def get_feed(self, feed_id: str) -> Optional[FeedConfig]:
        return self.feeds.get(feed_id)

    def add_or_update_feed(self, feed: FeedConfig) -> FeedConfig:
        self.feeds[feed.id] = feed
        self.save_feeds()
        return feed

    def delete_feed(self, feed_id: str) -> bool:
        if feed_id in self.feeds:
            del self.feeds[feed_id]
            self.save_feeds()
            return True
        return False

    def ensure_seeded(self) -> int:
        """Seeds default product data into SQLite/Postgres if the database is currently empty."""
        db = get_database_adapter()
        stats = db.get_stats()
        current_count = stats.get("total_cached_products", 0)
        if current_count == 0:
            print(f"[CatalogManager] Database is empty. Seeding {len(DEFAULT_SEED_PRODUCTS)} initial Romanian grocery & tech items...")
            self.ingest_items(DEFAULT_SEED_PRODUCTS)
            return len(DEFAULT_SEED_PRODUCTS)
        return 0

    def ingest_items(self, items: List[StoreResult]) -> int:
        """Ingests a list of StoreResult items, enriching physical store branch data."""
        if not items:
            return 0

        # Enrich with store branches
        for idx, it in enumerate(items):
            if not it.store_branch:
                branch = attach_branch_info(it.store_name, idx)
                if branch:
                    it.store_branch = branch.get("store_branch")
                    it.store_address = branch.get("store_address")
                    it.latitude = branch.get("latitude")
                    it.longitude = branch.get("longitude")

        db = get_database_adapter()
        if hasattr(db, "batch_save_catalog_products"):
            db.batch_save_catalog_products(items)
        else:
            db.save_cached_products("catalog", items[0].country_code if items else "RO", items)
        return len(items)

    async def download_feed_file(self, feed_url: str, dest_path: str) -> None:
        """Downloads a remote feed to a temporary file via streaming HTTP GET."""
        headers = {
            "User-Agent": "StoreStock-CatalogEngine/1.0 (+https://github.com/rappar222/storestock)",
            "Accept": "*/*"
        }
        try:
            import httpx
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                async with client.stream("GET", feed_url, headers=headers) as resp:
                    if resp.status_code >= 400:
                        raise RuntimeError(f"HTTP {resp.status_code} while downloading feed: {resp.reason_phrase}")
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
            return
        except ImportError:
            pass

        # Fallback to urllib
        def _sync_download():
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as response, open(dest_path, "wb") as out_file:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    out_file.write(chunk)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_download)

    async def sync_feed(self, feed_id: str) -> CatalogSyncResult:
        """Downloads and imports a single feed into the persistent database."""
        feed = self.feeds.get(feed_id)
        if not feed:
            return CatalogSyncResult(feed_id=feed_id, store_name="Unknown", success=False, error="Feed ID not found")

        t0 = time.time()
        temp_file = None
        is_temp = False

        try:
            feed.last_status = "Syncing..."
            self.save_feeds()

            # 1. Obtain local file path
            if os.path.exists(feed.feed_url):
                feed_path = feed.feed_url
            else:
                suffix = os.path.splitext(feed.feed_url.split("?")[0])[1] or ".tmp"
                fd, temp_file = tempfile.mkstemp(prefix=f"feed_{feed.id}_", suffix=suffix)
                os.close(fd)
                is_temp = True
                await self.download_feed_file(feed.feed_url, temp_file)
                feed_path = temp_file

            # 2. Stream and batch ingest
            batch: List[StoreResult] = []
            parsed_count = 0
            saved_count = 0

            for item in stream_feed_products(feed_path, feed):
                parsed_count += 1
                batch.append(item)
                if len(batch) >= 1000:
                    saved_count += self.ingest_items(batch)
                    batch = []

            if batch:
                saved_count += self.ingest_items(batch)

            elapsed = round(time.time() - t0, 2)
            feed.last_sync = int(time.time())
            feed.last_status = f"Success ({saved_count} items in {elapsed}s)"
            feed.items_count = saved_count
            self.save_feeds()

            return CatalogSyncResult(
                feed_id=feed.id,
                store_name=feed.store_name,
                success=True,
                items_parsed=parsed_count,
                items_saved=saved_count,
                duration_seconds=elapsed
            )

        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            error_msg = str(e)
            feed.last_sync = int(time.time())
            feed.last_status = f"Failed: {error_msg}"
            self.save_feeds()
            return CatalogSyncResult(
                feed_id=feed.id,
                store_name=feed.store_name,
                success=False,
                error=error_msg,
                duration_seconds=elapsed
            )
        finally:
            if is_temp and temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    async def sync_all_active_feeds(self) -> List[CatalogSyncResult]:
        """Runs sync for all enabled feeds."""
        results = []
        for feed in self.feeds.values():
            if feed.enabled:
                res = await self.sync_feed(feed.id)
                results.append(res)
        return results

_catalog_manager: Optional[CatalogManager] = None

def get_catalog_manager() -> CatalogManager:
    global _catalog_manager
    if _catalog_manager is None:
        _catalog_manager = CatalogManager()
    return _catalog_manager
