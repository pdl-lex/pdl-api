import numpy as np
import pandas as pd
import pytest

from app.transformers.standoff.character_map import CharacterMap


def is_equal(this: pd.DataFrame, other: pd.DataFrame) -> bool:
    return this.to_dict() == other.to_dict()


@pytest.fixture
def simple_spans():
    data = {
        "start": [0, 1, 2, 7, 16, 17, 21],
        "end": [37, 36, 6, 12, 35, 20, 34],
        "depth": [0, 1, 2, 2, 2, 3, 3],
        "tag": ["paragraph", "sent", "tok", "tok", "nounphrase", "tok", "tok"],
        "attributes": [{}, {}, {}, {}, {}, {}, {}],
        "text": [
            "   Das  ist      ein Beispielsatz  . ",
            "  Das  ist      ein Beispielsatz  .",
            " Das",
            " ist ",
            " ein Beispielsatz  ",
            "ein",
            "Beispielsatz ",
        ],
        "tag_id": [
            "paragraph_1",
            "sent_1",
            "tok_1",
            "tok_2",
            "nounphrase_1",
            "tok_3",
            "tok_4",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def simple_character_map(simple_spans):
    data = {
        "char": list("   Das  ist      ein Beispielsatz  . "),
        "depth_0": "paragraph_1",
        "depth_1": [
            np.nan,
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            "sent_1",
            np.nan,
        ],
        "depth_2": [
            np.nan,
            np.nan,
            "tok_1",
            "tok_1",
            "tok_1",
            "tok_1",
            np.nan,
            "tok_2",
            "tok_2",
            "tok_2",
            "tok_2",
            "tok_2",
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            "nounphrase_1",
            np.nan,
            np.nan,
        ],
        "depth_3": [
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            "tok_3",
            "tok_3",
            "tok_3",
            np.nan,
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            "tok_4",
            np.nan,
            np.nan,
            np.nan,
        ],
    }
    return CharacterMap(
        pd.DataFrame(data),
        span_attributes={
            "paragraph_1": {},
            "sent_1": {},
            "tok_1": {},
            "tok_2": {},
            "nounphrase_1": {},
            "tok_3": {},
            "tok_4": {},
        },
    )


@pytest.fixture
def character_map_with_adjacent_spans():
    data = pd.DataFrame(
        {
            "start": [0, 0, 5],
            "end": [10, 5, 10],
            "depth": [0, 1, 1],
            "tag": ["ROOT", "A", "B"],
            "tag_id": ["ROOT_1", "A_1", "B_1"],
            "text": ["aaaaabbbbb", "aaaaa", "bbbbb"],
            "attributes": [{}, {}, {}],
        }
    )
    return CharacterMap.from_spans(data)


def test_from_spans(simple_spans, simple_character_map):
    cmap = CharacterMap.from_spans(simple_spans)
    assert is_equal(cmap.df, simple_character_map.df)


def test_to_spans(simple_spans, simple_character_map):
    assert is_equal(simple_character_map.to_spans(), simple_spans)


def test_normalize_whitespace(simple_character_map):
    cmap = simple_character_map.normalize_ws()

    assert cmap.text == " Das ist ein Beispielsatz . "


def test_tighten_spans(simple_character_map):
    cmap = simple_character_map.tighten_spans()
    texts = cmap.to_spans().text

    assert not texts.str.match(r"^\s+|\s+$").any()


def test_pop_span(simple_character_map):
    cmap = simple_character_map.tighten_spans()
    popped = cmap.pop_span("nounphrase_1")

    assert simple_character_map.text == "Das ist  ."
    assert popped.text == "ein Beispielsatz"


@pytest.mark.parametrize(
    "index,text,expected",
    [
        (0, "[...]", "[...]Das ist ein Beispielsatz ."),
        (8, "noch ", "Das ist noch ein Beispielsatz ."),
        (
            len("Das ist ein Beispielsatz ."),
            " etc.",
            "Das ist ein Beispielsatz . etc.",
        ),
    ],
)
def test_basic_insert(simple_character_map, index, text, expected):
    cmap = simple_character_map.tighten_spans()
    assert cmap.insert(index, text).text == expected


def test_insert_without_host_span(character_map_with_adjacent_spans):
    cmap = character_map_with_adjacent_spans
    cmap.insert(5, " ")

    assert cmap.text == "aaaaa bbbbb"
    assert pd.isna(cmap.df.loc[5, "depth_1"])


@pytest.mark.parametrize("host_span", ["A_1", "B_1", "ROOT_1"])
def test_insert_with_host_span(character_map_with_adjacent_spans, host_span):
    # The specified host should enclose the inserted text
    cmap = character_map_with_adjacent_spans
    cmap.insert(5, " ", host_span)

    assert cmap.text == "aaaaa bbbbb"

    host = cmap.df.loc[5, "depth_1"]

    if host_span == "ROOT_1":
        assert pd.isna(host)
    else:
        assert host == host_span


def test_insert_recovers_interrupted_spans(character_map_with_adjacent_spans):
    cmap = character_map_with_adjacent_spans
    cmap.insert(4, " ")

    assert cmap.text == "aaaa abbbbb"
    assert cmap.df.loc[4, "depth_0"] == "ROOT_1"
    assert cmap.df.loc[4, "depth_1"] == "A_1"
