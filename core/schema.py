from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class StockLevel(str, Enum):
    IN_STOCK = "IN_STOCK"
    ONLINE_STOCK = "ONLINE_STOCK"
    LOW_STOCK = "LOW_STOCK"
    STORE_PICKUP_ONLY = "STORE_PICKUP_ONLY"
    PREORDER = "PREORDER"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"

class ProductCategory(str, Enum):
    TECH_HARDWARE = "tech_hardware"
    GROCERIES = "groceries"
    AUTOMOTIVE = "automotive"
    GENERAL = "general"

class StoreResult(BaseModel):
    id: str
    store_name: str
    store_icon: Optional[str] = None
    country_code: str
    title: str
    price: float
    currency: str = "RON"
    in_stock: bool
    stock_level: StockLevel = StockLevel.IN_STOCK
    stock_badge_text: str = "In Stock"
    stock_qty: Optional[int] = None
    product_url: str
    image_url: Optional[str] = None
    category: ProductCategory = ProductCategory.GENERAL
    brand: Optional[str] = None
    sku: Optional[str] = None
    delivery_info: Optional[str] = None
    store_branch: Optional[str] = None
    store_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    country_code: str
    total_results: int
    in_stock_count: int
    execution_time_ms: float
    stores_searched: List[str]
    ai_intent: Optional[dict] = None
    results: List[StoreResult]

class RestockAlert(BaseModel):
    id: str
    query: str
    store_name: str
    target_price: Optional[float] = None
    email: Optional[str] = None
    product_title: Optional[str] = None
    product_url: Optional[str] = None
    is_triggered: bool = False
    created_at: str
    last_status: str = "Out of Stock"
    last_checked: Optional[str] = None
