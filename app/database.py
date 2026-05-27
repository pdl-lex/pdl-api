from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


def get_engine(database_url: str = "sqlite:///./app.db", echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo)


def create_db_and_tables(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def get_session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
