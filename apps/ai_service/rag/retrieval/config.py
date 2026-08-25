from flashrank import Ranker

TOP_K_CANDIDATES = 20
MAX_DISTANCE = 0.4  # cosine distance threshold: 0=identical, 1=opposite

ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global ranker
    if ranker is None:
        ranker = Ranker(model_name="ms-marco-MultiBERT-L-12")
    return ranker
