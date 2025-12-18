from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query

from app.models import Entry, Resource
from app.services.lemma_service import LemmaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    lemma_service = LemmaService()
    app.state.lemma_service = lemma_service

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/lemma/{lemma_id}")
def fetch_lemma_entry(lemma_id: str = "bwb__Datschi") -> Entry:
    return app.state.lemma_service.fetch_lemma(lemma_id)


@app.get("/search")
def free_text_search(
    q: str = "Suchwort", resource: Optional[list[Resource]] = Query(default=None)
) -> list[Entry]:
    return app.state.lemma_service.free_text_search(q, resource)
