from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from core.schema import ProductCategory

class FeedFormat(str, Enum):
    AUTO = "auto"
    CSV = "csv"
    XML = "xml"
    JSON = "json"
    GOOGLE_MERCHANT = "google_merchant"
    TWO_PERFORMANT = "2performant"
    PROFITSHARE = "profitshare"

class FeedConfig(BaseModel):
    id: str
    name: str
    store_name: str
    store_icon: str = "shopping-bag"
    country_code: str = "RO"
    category: ProductCategory = ProductCategory.GENERAL
    feed_url: str
    feed_format: FeedFormat = FeedFormat.AUTO
    enabled: bool = True
    delimiter: Optional[str] = None
    field_mappings: Optional[Dict[str, str]] = None
    currency: str = "RON"
    affiliate_code: Optional[str] = None
    last_sync: Optional[int] = None
    last_status: Optional[str] = None
    items_count: Optional[int] = 0

class CatalogSyncResult(BaseModel):
    feed_id: str
    store_name: str
    success: bool
    items_parsed: int = 0
    items_saved: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
