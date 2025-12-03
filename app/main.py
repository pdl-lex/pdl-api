from fastapi import Depends, FastAPI

from app.services.lemma_service import LemmaService

app = FastAPI()


@app.get("/lemma/{lemma}")
def get_lemma(lemma: str, lemma_service: LemmaService = Depends(LemmaService)):
    return lemma_service.query_lemma(lemma)
