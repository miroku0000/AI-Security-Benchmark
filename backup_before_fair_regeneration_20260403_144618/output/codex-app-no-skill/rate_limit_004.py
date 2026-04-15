def normalize_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    source = hit.get("_source", {})
    return {
        "id": hit.get("_id"),
        "score": hit.get("_score"),
        "name": source.get("name"),
        "brand": source.get("brand"),
        "category": source.get("category"),
        "description": source.get("description"),
        "sku": source.get("sku"),
        "price": source.get("price"),
        "currency": source.get("currency"),
        "in_stock": source.get("in_stock"),
        "image_url": source.get("image_url"),
    }