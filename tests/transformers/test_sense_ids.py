import lxml.etree as ET  # noqa: N812

from app.transformers.base_xml_transformer import assign_missing_sense_ids
from app.transformers.dwds.dwds_transformer import transform_sense


def test_missing_sense_ids_are_derived_from_position():
    senses = [
        {"sourceId": "kept", "sense": [{"sourceId": None, "sense": []}]},
        {"sourceId": None, "sense": [{"sourceId": None, "sense": []}]},
    ]

    assign_missing_sense_ids(senses, "entry")

    assert senses[0]["sourceId"] == "kept"
    assert senses[0]["sense"][0]["sourceId"] == "entry/sense/1.1"
    assert senses[1]["sourceId"] == "entry/sense/2"
    assert senses[1]["sense"][0]["sourceId"] == "entry/sense/2.1"


def test_missing_sense_ids_stay_empty_without_entry_id():
    senses = [{"sourceId": None, "sense": []}]

    assign_missing_sense_ids(senses, None)

    assert senses[0]["sourceId"] is None


def test_dwds_sense_reads_xml_id():
    node = ET.fromstring(
        '<Lesart xml:id="S_1" n="1."><Definition>Def</Definition>'
        "<Lesart><Definition>Sub</Definition></Lesart></Lesart>"
    )

    sense = transform_sense(node)

    assert sense["sourceId"] == "S_1"
    assert sense["sense"][0]["sourceId"] is None
