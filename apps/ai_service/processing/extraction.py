import io

from pypdf import PdfReader


def extract_pages(file_obj) -> list[tuple[int, str]]:
    """Return [(page_number, text), ...] for each non-empty page."""
    pdf_bytes = io.BytesIO(file_obj.read())
    reader = PdfReader(pdf_bytes)
    pages = []
    
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages
