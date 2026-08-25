from apps.ai_service.utils import mime_type_for_bytes


class TestMimeTypeForBytes:
    def test_png_magic_bytes(self):
        data = b"\x89PNG\r\n\x1a\nsome png data"
        assert mime_type_for_bytes(data) == "image/png"

    def test_webp_magic_bytes(self):
        data = b"RIFF\x00\x00\x00\x00WEBP extra"
        assert mime_type_for_bytes(data) == "image/webp"

    def test_jpeg_default_for_jpeg_header(self):
        data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        assert mime_type_for_bytes(data) == "image/jpeg"

    def test_unknown_bytes_default_to_jpeg(self):
        assert mime_type_for_bytes(b"\x00\x00\x00\x00") == "image/jpeg"

    def test_empty_bytes_default_to_jpeg(self):
        assert mime_type_for_bytes(b"") == "image/jpeg"

    def test_riff_without_webp_marker_is_jpeg(self):
        data = b"RIFF\x00\x00\x00\x00AVI "
        assert mime_type_for_bytes(data) == "image/jpeg"

    def test_partial_png_header_is_jpeg(self):
        data = b"\x89PN"  # Only 3 bytes — not a full PNG header
        assert mime_type_for_bytes(data) == "image/jpeg"
