from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class StockLevel(str, Enum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    STORE_PICKUP_ONLY = "STORE_PICKUP_ONLY"
    PREORDER = "PREORDER"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"

class ProductCategory(str, Enum):
    TECH_HARDWARE = "tech_hardware"
    GROCERIES = "groceries"
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

class SearchResponse(BaseModel):
    query: str
    country_code: str
    total_results: int
    in_stock_count: int
    execution_time_ms: float
    stores_searched: List[str]
    results: List[StoreResult]
