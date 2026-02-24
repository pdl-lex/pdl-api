import gzip
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.entry import Entry, EntryList, KeywordList, Resource
from app.models.query_summary import QuerySummary
from app.services.import_service import ImportService
from app.services.query_service import QueryService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_KEY = os.environ["MONGO_API_KEY"]


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    query_service = QueryService()
    app.state.query_service = query_service

    import_service = ImportService()
    app.state.import_service = import_service

    yield


class DecompressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("Content-Encoding") == "gzip":
            body = await request.body()
            request._body = gzip.decompress(body)
        return await call_next(request)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ["ALLOWED_ORIGINS"].split(";"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DecompressMiddleware)


@app.get("/lemma-display/{lemma_id}")
def fetch_lemma_display_entry(lemma_id: str = "bwb__Datschi") -> Entry:
    return app.state.query_service.fetch_lemma_display(lemma_id)


@app.get("/search")
def free_text_search(
    q: Optional[str] = None,
    lemma: Optional[str] = Query(default=None),
    pos: Optional[str] = Query(default=None),
    npos: Optional[str] = Query(default=None),
    resources: Optional[list[Resource]] = Query(default=None),
    page: int = 1,
    results_per_page: int = 10,
) -> EntryList:
    query_service: QueryService = app.state.query_service

    return query_service.free_text_search(
        term=q,
        lemma=lemma,
        page=page,
        results_per_page=results_per_page,
        resources=resources,
        pos=pos,
        npos=npos,
    )


@app.get("/summary")
def query_summary(
    q: Optional[str] = None,
    lemma: Optional[str] = Query(default=None),
    pos: Optional[str] = Query(default=None),
    npos: Optional[str] = Query(default=None),
    resources: Optional[list[Resource]] = Query(default=None),
    page: int = 1,
    results_per_page: int = 10,
) -> QuerySummary:
    query_service: QueryService = app.state.query_service

    return query_service.query_summary(
        term=q,
        lemma=lemma,
        page=page,
        results_per_page=results_per_page,
        resources=resources,
        pos=pos,
        npos=npos,
    )


@app.post("/upload")
def upload(data: list[Entry], _api_key: str = Depends(verify_api_key)):
    logger.info(f"Starting insert operation for {len(data)} entries")
    import_service: ImportService = app.state.import_service

    try:
        result = import_service.insert_data(data)
        logger.info(f"Successfully inserted {result['inserted_count']} documents")
        return {
            "status": "success",
            "inserted_count": result["inserted_count"],
            "message": f"Successfully inserted {result['inserted_count']} documents",
        }
    except Exception as err:
        logger.error(f"Insert operation failed: {str(err)}")
        raise HTTPException(
            status_code=500, detail=f"Insert operation failed: {str(err)}"
        ) from err


@app.get("/keywords/{letter}")
def get_by_letter(
    letter: str | None, page: int = 1, results_per_page: int = 10
) -> KeywordList:
    query_service: QueryService = app.state.query_service

    return query_service.fetch_keywords(
        letter, page=page, results_per_page=results_per_page
    )
