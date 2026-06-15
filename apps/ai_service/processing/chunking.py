CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_STEP = CHUNK_SIZE - CHUNK_OVERLAP
assert _STEP > 0, "CHUNK_OVERLAP must be less than CHUNK_SIZE"


def chunk_page(text: str, page_number: int) -> list[dict]:
    """Split a page's text into overlapping chunks aligned to word boundaries."""
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + CHUNK_SIZE

        # Snap end to the nearest word boundary (don't cut mid-word).
        if end < length:
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"content": chunk, "page_number": page_number})

        start += _STEP

    return chunks
