from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def bdo_simple_xml_path(fixture_dir):
    return fixture_dir / "xml_data/bdo/simple_entry.xml"


@pytest.fixture
def bdo_simple_json_path(fixture_dir):
    return fixture_dir / "json_data/bdo/simple_entry.json"


@pytest.fixture
def bdo_simple_json(bdo_simple_json_path):
    import json

    with open(bdo_simple_json_path) as f:
        return json.load(f)


@pytest.fixture
def bdo_transformer():
    from app.transformers.bdo.bdo_transformer import BdoXmlTransformer

    return BdoXmlTransformer()


@pytest.fixture
def bdo_complex_etymology(fixture_dir):
    import lxml.etree as ET  # noqa: N812

    return ET.parse(fixture_dir / "xml_data/bdo/complex_etymology.xml").getroot()


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
