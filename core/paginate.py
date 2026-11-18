def paginate(items: list, per_page: int) -> list[list]:
    """Split items into pages; no items means no pages."""
    per_page = max(1, per_page)
    return [items[i:i + per_page] for i in range(0, len(items), per_page)]
