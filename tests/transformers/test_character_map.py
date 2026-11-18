import pytest

from app.transformers.standoff.character_map import CharacterMap, Span


def ranges(cmap: CharacterMap) -> dict[str, tuple[int, int]]:
    return {span.span_id: (span.start, span.end) for span in cmap.to_spans()}


@pytest.fixture
def simple_character_map():
    spans = [
        Span("paragraph_1", "paragraph", 0, 0, 37),
        Span("sent_1", "sent", 1, 1, 36),
        Span("tok_1", "tok", 2, 2, 6),
        Span("tok_2", "tok", 2, 7, 12),
        Span("nounphrase_1", "nounphrase", 2, 16, 35),
        Span("tok_3", "tok", 3, 17, 20),
        Span("tok_4", "tok", 3, 21, 34),
    ]
    return CharacterMap(
        "   Das  ist      ein Beispielsatz  . ",
        spans,
        span_attributes={span.span_id: {} for span in spans},
    )


@pytest.fixture
def character_map_with_adjacent_spans():
    spans = [
        Span("ROOT_1", "ROOT", 0, 0, 10),
        Span("A_1", "A", 1, 0, 5),
        Span("B_1", "B", 1, 5, 10),
    ]
    return CharacterMap("aaaaabbbbb", spans, {s.span_id: {} for s in spans})


def test_to_spans(simple_character_map):
    spans = simple_character_map.to_spans()

    assert [s.span_id for s in spans] == [
        "paragraph_1",
        "sent_1",
        "tok_1",
        "tok_2",
        "nounphrase_1",
        "tok_3",
        "tok_4",
    ]
    assert [s.text for s in spans] == [
        "   Das  ist      ein Beispielsatz  . ",
        "  Das  ist      ein Beispielsatz  .",
        " Das",
        " ist ",
        " ein Beispielsatz  ",
        "ein",
        "Beispielsatz ",
    ]


def test_normalize_whitespace(simple_character_map):
    cmap = simple_character_map.normalize_ws()

    assert cmap.text == " Das ist ein Beispielsatz . "


def test_minify(simple_character_map):
    cmap = simple_character_map.minify()

    for span in cmap.to_spans():
        assert span.text == span.text.strip()


def test_pop_span(simple_character_map):
    cmap = simple_character_map.minify()
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
    cmap = simple_character_map.minify()
    assert cmap.insert(index, text).text == expected


def test_insert_without_host_span(character_map_with_adjacent_spans):
    cmap = character_map_with_adjacent_spans
    cmap.insert(5, " ")

    assert cmap.text == "aaaaa bbbbb"
    assert ranges(cmap) == {"ROOT_1": (0, 11), "A_1": (0, 5), "B_1": (6, 11)}


@pytest.mark.parametrize(
    "host_span,expected",
    [
        ("A_1", {"ROOT_1": (0, 11), "A_1": (0, 6), "B_1": (6, 11)}),
        ("B_1", {"ROOT_1": (0, 11), "A_1": (0, 5), "B_1": (5, 11)}),
        ("ROOT_1", {"ROOT_1": (0, 11), "A_1": (0, 5), "B_1": (6, 11)}),
    ],
)
def test_insert_with_host_span(character_map_with_adjacent_spans, host_span, expected):
    # The specified host should enclose the inserted text
    cmap = character_map_with_adjacent_spans
    cmap.insert(5, " ", host_span)

    assert cmap.text == "aaaaa bbbbb"
    assert ranges(cmap) == expected


def test_insert_recovers_interrupted_spans(character_map_with_adjacent_spans):
    cmap = character_map_with_adjacent_spans
    cmap.insert(4, " ")

    assert cmap.text == "aaaa abbbbb"
    assert ranges(cmap) == {"ROOT_1": (0, 11), "A_1": (0, 6), "B_1": (6, 11)}


def test_spans(simple_character_map):
    assert sorted(simple_character_map.spans()) == [
        "nounphrase_1",
        "paragraph_1",
        "sent_1",
        "tok_1",
        "tok_2",
        "tok_3",
        "tok_4",
    ]
    assert sorted(simple_character_map.spans("tok")) == [
        "tok_1",
        "tok_2",
        "tok_3",
        "tok_4",
    ]


def test_add_span(simple_character_map):
    start = 4
    end = 7
    attributes = {"baz": 42}

    simple_character_map.add_span("foobar", start, end, attributes)
    span = next(s for s in simple_character_map.to_spans() if s.span_id == "foobar_1")

    assert [span.start, span.end, span["baz"]] == [start, end, 42]


def test_set_text_discards_subspans():
    spans = [
        Span("ROOT_1", "ROOT", 0, 0, 12),
        Span("ref_1", "ref", 1, 2, 10),
        Span("lemma_1", "lemma", 2, 2, 5),
        Span("hoch_1", "hoch", 3, 2, 3),
        Span("hoch_2", "hoch", 3, 4, 5),
        Span("tail_1", "tail", 1, 10, 12),
    ]
    cmap = CharacterMap("a 2x3 Bed.zz", spans, {s.span_id: {} for s in spans})

    cmap.set_text("lemma_1", "Haus, ")

    assert cmap.text == "a Haus,  Bed.zz"
    assert ranges(cmap) == {
        "ROOT_1": (0, 15),
        "ref_1": (2, 13),
        "lemma_1": (2, 8),
        "tail_1": (13, 15),
    }
