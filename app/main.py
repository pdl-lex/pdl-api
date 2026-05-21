import gzip
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, select

from app.database import engine, get_session
from app.models.entry import Entry, EntryList, KeywordList, Resource
from app.models.query_summary import QuerySummary
from app.services.import_service import ImportService
from app.services.query_service import QueryService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_KEY = os.environ["API_UPLOAD_KEY"]


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
    SQLModel.metadata.create_all(engine)

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ["ALLOWED_ORIGINS"].split(";"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/lemma/{lemma_id:path}", tags=["Search"])
def fetch_lemma_display_entry(lemma_id: str = "bwb__Datschi") -> Entry:
    return app.state.query_service.fetch_lemma_display(lemma_id)


@app.get("/search", tags=["Search"])
def complex_search(
    q: Optional[str] = None,
    lemma: Optional[str] = Query(default=None),
    pos: Optional[str] = Query(default=None),
    npos: Optional[str] = Query(default=None),
    resources: Optional[list[Resource]] = Query(default=None),
    senses: Optional[str] = None,
    etymology: Optional[str] = None,
    page: int = 1,
    results_per_page: int = 10,
) -> EntryList:
    query_service: QueryService = app.state.query_service

    return query_service.complex_search(
        term=q,
        lemma=lemma,
        page=page,
        results_per_page=results_per_page,
        resources=resources,
        pos=pos,
        npos=npos,
        senses=senses,
        etymology=etymology,
    )


@app.get("/summary", tags=["Search"])
def query_summary(
    q: Optional[str] = None,
    lemma: Optional[str] = Query(default=None),
    pos: Optional[str] = Query(default=None),
    npos: Optional[str] = Query(default=None),
    resources: Optional[list[Resource]] = Query(default=None),
    senses: Optional[str] = None,
    etymology: Optional[str] = None,
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
        senses=senses,
        etymology=etymology,
    )


@app.post("/upload", include_in_schema=False)
async def upload(
    file: UploadFile, resource: Resource, _api_key: str = Depends(verify_api_key)
):
    logger.info(f"Starting {resource.value} update")
    import_service: ImportService = app.state.import_service

    content = await file.read()

    logger.info(f"Decompressing data")
    lines = gzip.decompress(content).decode("utf-8").splitlines()

    logger.info(f"Loading data")

    logger.info(f"Inserting entries into db")

    try:
        result = import_service.insert_data(
            (json.loads(line) for line in lines if line.strip()), resource=resource
        )
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


@app.get("/keywords/{letter}", tags=["Search"])
def get_by_letter(
    letter: str | None, page: int = 1, results_per_page: int = 10
) -> KeywordList:
    query_service: QueryService = app.state.query_service

    return query_service.fetch_keywords(
        letter, page=page, results_per_page=results_per_page
    )


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str


@app.post("/users/", response_model=User)
def create_user(user: User, session: Session = Depends(get_session)):
    """Create a new user"""
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/users/", response_model=list[User])
def list_users(session: Session = Depends(get_session)):
    """List all users"""
    users = session.exec(select(User)).all()
    return users
