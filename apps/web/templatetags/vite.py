import json
from functools import cache
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


def _read_manifest() -> dict:
    manifest_path = Path(settings.BASE_DIR) / "static" / "manifest.json"
    if not manifest_path.exists():
        return {}
    with manifest_path.open(encoding="utf-8") as f:
        return json.load(f)


@cache
def _cached_manifest() -> dict:
    return _read_manifest()


def _get_manifest() -> dict:
    # Re-read under DEBUG so a rebuild shows up without a restart.
    return _read_manifest() if settings.DEBUG else _cached_manifest()


@register.simple_tag
def vite_asset(entry: str) -> str:
    manifest = _get_manifest()
    if entry in manifest:
        return static(manifest[entry]["file"])
    return static(entry)
