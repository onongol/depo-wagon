import json
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()

_manifest_cache: dict | None = None


def _get_manifest() -> dict:
    global _manifest_cache
    if _manifest_cache is None or settings.DEBUG:
        manifest_path = Path(settings.BASE_DIR) / "static" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                _manifest_cache = json.load(f)
        else:
            _manifest_cache = {}
    return _manifest_cache


@register.simple_tag
def vite_asset(entry: str) -> str:
    manifest = _get_manifest()
    if entry in manifest:
        return static(manifest[entry]["file"])
    return static(entry)
