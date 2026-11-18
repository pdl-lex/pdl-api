import lxml.etree as ET  # noqa: N812
import pytest

from app.transformers.bdo.bdo_mixed_content import BdoMixedContentTransformer


def serialize(xml: str) -> dict:
    return BdoMixedContentTransformer.load_xml(ET.fromstring(xml)).serialize()


def assert_offsets_match(result: dict) -> None:
    for annotation in result["annotations"]:
        start, end = annotation["start"], annotation["end"]
        assert result["text"][start:end] == annotation["text"]


@pytest.mark.parametrize(
    "xml,expected",
    [
        (
            '<e>A <verweis verweis-typ="siehe" ziel="x" ziel-typ="Lemma">foo</verweis>'
            ' B <verweis verweis-typ="vgl." ziel="y" ziel-typ="Lemma">bar</verweis>.</e>',
            "A siehe foo B vgl. bar.",
        ),
        (
            '<e><verweis verweis-typ="Pfeil" ziel="x_1" ziel-typ="Bedeutung">'
            '<lemma-referenz vollform="unten">u.</lemma-referenz>1</verweis> und '
            '<verweis verweis-typ="siehe" ziel="y" ziel-typ="Lemma">weg</verweis></e>',
            "unten, Bed. 1 und siehe weg",
        ),
    ],
)
def test_crossref_prefixes_follow_earlier_insertions(xml, expected):
    result = serialize(xml)

    assert result["text"] == expected
    assert_offsets_match(result)


def test_expanded_lemma_keeps_homograph_index():
    result = serialize(
        '<e>(wie <verweis verweis-typ="Pfeil" ziel="blechen2_4" ziel-typ="Bedeutung">'
        '<lemma-referenz vollform="blechen">b.<hoch>2</hoch>\n</lemma-referenz>4'
        "</verweis>)</e>"
    )

    assert result["text"] == "(wie blechen2, Bed. 4)"
    superscript = {
        "type": "text",
        "start": 12,
        "end": 13,
        "text": "2",
        "labels": ["superscript"],
    }
    assert superscript in result["annotations"]
    assert_offsets_match(result)


def bibrefs(result: dict) -> dict[str, dict]:
    return {a["text"]: a for a in result["annotations"] if a["type"] == "bibref"}


def test_each_bibref_gets_its_own_details():
    result = serialize(
        '<e><literatur-quelle literatur="a"><werk>A</werk>'
        "<details><titel>Details A</titel></details></literatur-quelle>; "
        '<literatur-quelle literatur="b"><werk>B</werk>'
        "<details><titel>Details B</titel></details></literatur-quelle>.</e>"
    )

    refs = bibrefs(result)
    assert result["text"] == "A; B."
    assert refs["A"]["fullReference"]["text"] == "Details A"
    assert refs["B"]["fullReference"]["text"] == "Details B"


def test_bibref_without_details_has_no_full_reference():
    result = serialize(
        '<e><literatur-quelle literatur="a"><werk>A</werk>'
        "<details><titel>Details A</titel></details></literatur-quelle>; "
        "<literatur-quelle><werk>Much in: ZDW 11</werk></literatur-quelle>.</e>"
    )

    refs = bibrefs(result)
    assert refs["A"]["fullReference"]["text"] == "Details A"
    assert refs["Much in: ZDW 11"]["fullReference"] is None
