import lxml.etree as ET  # noqa: N812
import pytest

from app.models.annotated_text import TextAnnotationSpan
from app.transformers.standoff.standoff_transformer import (
    StandoffTransformer,
    register,
    xml_to_standoff,
)


@pytest.fixture
def basic_annotated_xml():
    xml = """<satz><pronomen>Das</pronomen> <verb>ist</verb> <artikel>ein</artikel> 
    <nomen>Beispielsatz</nomen>.</satz>"""

    return ET.fromstring(xml)


@pytest.fixture
def complex_whitespace_xml():
    xml = """
    <satz>
        <pronomen>Das</pronomen>
        <verb>ist</verb>
        <artikel>ein</artikel>  <adjektiv>komplexer</adjektiv>
        <nomen>
        <kompositum vollform="Beispielsatz"><mod>Beispiel</mod><kopf>satz</kopf></kompositum>
        </nomen>
        mit

        zusätzlichen         Leerzeichen und leeren <br /> Tags <trace />.
        </satz>
    """

    return ET.fromstring(xml)


@pytest.fixture
def complex_annotated_xml():
    xml = """
    <text>
        <zusammenfassung lemmaId="ahorn_n">
            <lemma>Ahorn</lemma>, <fremdsprache sprache="latein">lat. Acer</fremdsprache>,
            <bedeutung>Bezeichnung für einen Laubbaum mit charakteristischen, meist handförmig
            gelappten Blättern;</bedeutung>
            <referenz ziel="eintrag-x">vgl. Eintrag x</referenz> und
            <referenz ziel="eintrag-y">Eintrag y</referenz>.
            <verbreitung>Die Art ist in mitteleuropäischen Wäldern und Parks weit
            verbreitet (<literatur id="meier96" typ="vgl."><autor>Meier</autor>, 
            <jahr>1996</jahr>)</literatur></verbreitung>.
        </zusammenfassung>
    </text>
    """

    return ET.fromstring(xml)


@pytest.fixture
def complex_spans():
    return [
        [
            0,
            343,
            0,
            "text",
            {},
            "\n        \n            Ahorn, lat. Acer,\n            Bezeichnung für einen Laubbaum "
            "mit charakteristischen, meist handförmig\n            gelappten Blättern;\n           "
            " vgl. Eintrag x und\n            Eintrag y.\n            Die Art ist in "
            "mitteleuropäischen Wäldern und Parks weit\n            verbreitet (Meier, \n"
            "            1996).\n        \n    ",
        ],
        [
            9,
            338,
            1,
            "zusammenfassung",
            {"lemmaId": "ahorn_n"},
            "\n            Ahorn, lat. Acer,\n            Bezeichnung für einen Laubbaum mit "
            "charakteristischen, meist handförmig\n            gelappten Blättern;\n"
            "            vgl. Eintrag x und\n            Eintrag y.\n            Die Art ist in "
            "mitteleuropäischen Wäldern und Parks weit\n            verbreitet (Meier, \n"
            "            1996).\n        ",
        ],
        [22, 27, 2, "lemma", {}, "Ahorn"],
        [29, 38, 2, "fremdsprache", {"sprache": "latein"}, "lat. Acer"],
        [
            52,
            155,
            2,
            "bedeutung",
            {},
            "Bezeichnung für einen Laubbaum mit charakteristischen, meist handförmig\n"
            "            gelappten Blättern;",
        ],
        [168, 182, 2, "referenz", {"ziel": "eintrag-x"}, "vgl. Eintrag x"],
        [199, 208, 2, "referenz", {"ziel": "eintrag-y"}, "Eintrag y"],
        [
            222,
            328,
            2,
            "verbreitung",
            {},
            "Die Art ist in mitteleuropäischen Wäldern und Parks weit\n"
            "            verbreitet (Meier, \n            1996)",
        ],
        [
            303,
            328,
            3,
            "literatur",
            {"id": "meier96", "typ": "vgl."},
            "Meier, \n            1996)",
        ],
        [303, 308, 4, "autor", {}, "Meier"],
        [323, 327, 4, "jahr", {}, "1996"],
    ]


def test_xml_to_standoff(complex_annotated_xml, complex_spans):
    spans = xml_to_standoff(complex_annotated_xml)
    assert spans == complex_spans


@pytest.fixture
def basic_transformer(basic_annotated_xml):
    class Transformer(StandoffTransformer):
        pass

    return Transformer.load_xml(basic_annotated_xml)


def test_basic_annotation(basic_transformer):
    expected = {
        "span_id": ["satz_1", "pronomen_1", "verb_1", "artikel_1", "nomen_1"],
        "start": [0, 0, 4, 8, 12],
        "end": [25, 3, 7, 11, 24],
        "tag": ["satz", "pronomen", "verb", "artikel", "nomen"],
        "depth": [0, 1, 1, 1, 1],
        "text": ["Das ist ein Beispielsatz.", "Das", "ist", "ein", "Beispielsatz"],
    }
    assert basic_transformer.cmap.to_spans().to_dict(orient="list") == expected


def test_basic_serialization(basic_transformer):
    assert basic_transformer.serialize() == {
        "text": "Das ist ein Beispielsatz.",
        "annotations": [],
    }


def test_registered_spans_are_returned(basic_annotated_xml):
    class Transformer(StandoffTransformer):
        @register("nomen")
        def serialize_noun(self, span):
            return TextAnnotationSpan(
                start=span.start,
                end=span.end,
                text=span.text,
                type="text",
                labels=["NOUN"],
            )

    result = Transformer.load_xml(basic_annotated_xml).serialize()

    assert result["annotations"] == [
        {
            "start": 12,
            "end": 24,
            "text": "Beispielsatz",
            "type": "text",
            "labels": ["NOUN"],
        }
    ]
