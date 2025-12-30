import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import DisplayEntry, DisplayEntryList, Entry, Resource
from app.services.import_service import ImportService
from app.services.lemma_service import LemmaService

ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://lexoterm.de",
]


API_KEY = os.environ["MONGO_API_KEY"]


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    lemma_service = LemmaService()
    app.state.lemma_service = lemma_service

    import_service = ImportService()
    app.state.import_service = import_service

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/lemma/{lemma_id}")
def fetch_lemma_entry(lemma_id: str = "bwb__Datschi") -> Entry:
    return app.state.lemma_service.fetch_lemma(lemma_id)


@app.get("/lemma-display/{lemma_id}")
def fetch_lemma_display_entry(lemma_id: str = "bwb__Datschi") -> DisplayEntry:
    return app.state.lemma_service.fetch_lemma_display(lemma_id)


@app.get("/search")
def free_text_search(
    q: str = "Suchwort",
    resources: Optional[list[Resource]] = Query(default=None),
    pos: Optional[str] = Query(default=None),
    npos: Optional[str] = Query(default=None),
    page: int = 1,
    results_per_page: int = 10,
) -> DisplayEntryList:
    lemma_service: LemmaService = app.state.lemma_service
    return lemma_service.free_text_search(
        q,
        page=page,
        results_per_page=results_per_page,
        resources=resources,
        pos=pos,
        npos=npos,
    )


@app.post("/insert-display-data")
def insert_display_data(
    data: list[DisplayEntry], _api_key: str = Depends(verify_api_key)
):
    import_service: ImportService = app.state.import_service

    import_service.insert_display_data(data)
