"""
Pagination Helper Module
"""
from typing import Dict, Any, List
import math

def paginate_list(items: List[Any], page: int = 1, limit: int = 50) -> Dict[str, Any]:
    total = len(items)
    page = max(1, page)
    limit = max(1, limit)
    total_pages = max(1, math.ceil(total / limit))
    offset = (page - 1) * limit
    paged_items = items[offset : offset + limit]
    return {
        "data": paged_items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }

