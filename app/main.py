from fastapi import Depends, FastAPI

from app.models import LemmaResult
from app.services.aggregator import Aggregator


def get_aggregator():
    return Aggregator()


app = FastAPI()


@app.get("/lemma/{key}")
def get_lemma(
    key: str, aggregator: Aggregator = Depends(get_aggregator)
) -> LemmaResult:
    return aggregator.query_lemma(key)
