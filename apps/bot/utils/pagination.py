def clamp_page(total: int, page: int, page_size: int) -> tuple[int, int]:
    """Number of pages, never less than one, and page pulled into range."""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return total_pages, max(0, min(page, total_pages - 1))
