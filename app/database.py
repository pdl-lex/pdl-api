import os

from dotenv import load_dotenv
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, create_engine

load_dotenv()


DATABASE_URL = os.environ["POSTGRES_URL"]

engine = create_engine(DATABASE_URL, echo=False, poolclass=QueuePool)


def get_session():
    with Session(engine) as session:
        yield session
