from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " ", ""],
)


def chunk_page(text: str, page_number: int) -> list[dict]:
    """
    Split page text into chunks,
    returning list of {"content": ..., "page_number": ...}.
    """
    return [
        {"content": chunk, "page_number": page_number}
        for chunk in _splitter.split_text(text)
        if chunk.strip()
    ]
