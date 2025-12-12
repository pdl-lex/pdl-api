from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.services.lemma_service import LemmaService


@asynccontextmanager
async def lifespan(app: FastAPI):
    lemma_service = LemmaService()
    app.state.lemma_service = lemma_service

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/lemma/{lemma}")
def get_lemma(lemma: str):
    return app.state.lemma_service.query_lemma(lemma)
