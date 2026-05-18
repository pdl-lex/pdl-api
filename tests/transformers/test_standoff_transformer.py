import lxml.etree as ET  # noqa: N812
import pytest

from app.models.annotated_text import TextAnnotationSpan
from app.transformers.standoff.standoff_transformer import StandoffTransformer, register
from app.transformers.standoff.xml_standoff_converter import xml_to_standoff


@pytest.fixture
def basic_annotated_xml():
    xml = """<satz><pronomen>Das</pronomen> <verb>ist</verb> <artikel>ein</artikel> 
    <nomen>Beispielsatz</nomen>.</satz>"""

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
            verbreitet <literatur id="meier96">(<autor>Meier</autor>, 
            <jahr>1996</jahr>)</literatur></verbreitung>.
        </zusammenfassung>
    </text>
    """

    return ET.fromstring(xml)


@pytest.fixture
def complex_spans():
    return [
        (
            0,
            226,
            0,
            "text",
            {},
            "  Ahorn, lat. Acer, Bezeichnung für einen Laubbaum mit charakteristischen, meist "
            "handförmig gelappten Blättern; vgl. Eintrag x und Eintrag y. Die Art ist in "
            "mitteleuropäischen Wäldern und Parks weit verbreitet (Meier, 1996).  ",
        ),
        (
            1,
            225,
            1,
            "zusammenfassung",
            {"lemmaId": "ahorn_n"},
            " Ahorn, lat. Acer, Bezeichnung für einen Laubbaum mit charakteristischen, meist "
            "handförmig gelappten Blättern; vgl. Eintrag x und Eintrag y. Die Art ist in "
            "mitteleuropäischen Wäldern und Parks weit verbreitet (Meier, 1996). ",
        ),
        (2, 7, 2, "lemma", {}, "Ahorn"),
        (9, 18, 2, "fremdsprache", {"sprache": "latein"}, "lat. Acer"),
        (
            20,
            111,
            2,
            "bedeutung",
            {},
            "Bezeichnung für einen Laubbaum mit charakteristischen, meist handförmig gelappten "
            "Blättern;",
        ),
        (112, 126, 2, "referenz", {"ziel": "eintrag-x"}, "vgl. Eintrag x"),
        (131, 140, 2, "referenz", {"ziel": "eintrag-y"}, "Eintrag y"),
        (
            142,
            223,
            2,
            "verbreitung",
            {},
            "Die Art ist in mitteleuropäischen Wäldern und Parks weit verbreitet (Meier, 1996)",
        ),
        (210, 223, 3, "literatur", {"id": "meier96"}, "(Meier, 1996)"),
        (211, 216, 4, "autor", {}, "Meier"),
        (218, 222, 4, "jahr", {}, "1996"),
    ]


def test_xml_to_standoff(complex_annotated_xml, complex_spans):
    spans = xml_to_standoff(complex_annotated_xml)
    assert spans == complex_spans


def test_empty_standoff_transformer(basic_annotated_xml):
    class Transformer(StandoffTransformer):
        pass

    result = Transformer.load_xml(basic_annotated_xml).serialize()
    assert result == {"text": "Das ist ein Beispielsatz.", "annotations": []}


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
