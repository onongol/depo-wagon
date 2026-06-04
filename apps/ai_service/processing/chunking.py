CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 100  # overlap between consecutive chunks


def chunk_page(text: str, page_number: int) -> list[dict]:
    """Split a page's text into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"content": chunk, "page_number": page_number})
        start = end - CHUNK_OVERLAP
    return chunks
