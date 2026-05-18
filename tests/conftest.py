from pathlib import Path

import pytest


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
