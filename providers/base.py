import abc
from typing import List
from core.schema import StoreResult, ProductCategory

class BaseProvider(abc.ABC):
    store_id: str
    store_name: str
    country_code: str
    category: ProductCategory
    store_icon: str = "shopping-bag"

    @abc.abstractmethod
    async def search(self, query: str) -> List[StoreResult]:
        """
        Query the store inventory and return normalized StoreResult objects.
        """
        pass
