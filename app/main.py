from fastapi import Depends, FastAPI

from app.models import LemmaResult
from app.services.aggregator import Aggregator

app = FastAPI()


@app.get("/lemma/{key}")
def get_lemma(key: str, aggregator: Aggregator = Depends(Aggregator)) -> LemmaResult:
    return aggregator.query_lemma(key)
