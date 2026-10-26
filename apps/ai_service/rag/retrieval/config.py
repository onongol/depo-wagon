from functools import cache

from django.conf import settings
from flashrank import Ranker

TOP_K_CANDIDATES = 20
MAX_DISTANCE = 0.4  # cosine distance threshold: 0=identical, 1=opposite


@cache
def get_ranker() -> Ranker:
    return Ranker(
        model_name="ms-marco-MultiBERT-L-12",
        cache_dir=str(settings.BASE_DIR / ".cache" / "flashrank"),
    )
