def mime_type_for_bytes(data: bytes) -> str:
    """Detect image MIME type from magic bytes; defaults to image/jpeg."""
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"
