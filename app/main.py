from fastapi import Depends, FastAPI

from app.models import Entry
from app.services.lemma_service import LemmaService

app = FastAPI()


@app.get("/lemma/{lemma_id}")
def fetch_lemma_entry(
    lemma_id: str, lemma_service: LemmaService = Depends(LemmaService)
) -> Entry:
    return lemma_service.fetch_lemma(lemma_id)


@app.get("/search")
def free_text_search(
    q: str = "Suchwort", lemma_service: LemmaService = Depends(LemmaService)
) -> list[Entry]:
    return lemma_service.free_text_search(q)
