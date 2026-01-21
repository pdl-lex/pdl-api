from functools import singledispatchmethod


def wrap_text(text, width=15):
    if len(text) > width:
        i = width // 2 - 1
        ellipsis = "." * (width - 2 * i)
        return "".join((text[:i], ellipsis, text[-i:]))
    return text


class ComparableSpan:
    @singledispatchmethod
    def has_overlap(self, other):
        return self.start < other.end and other.start < self.end

    @has_overlap.register
    def _(self, other_start: int, other_end: int):
        return self.start < other_end and other_start < self.end

    def __str__(self):
        return "<{} [{}..{}] {!r}>".format(
            self.__class__.__name__,
            self.start,
            self.end,
            wrap_text(self.text),
        )


class Span(ComparableSpan):
    _type = "span"

    def __init__(self, start, end, text, type, **kwargs):
        self.start = start
        self.end = end
        self.type = type
        self.text = text

    @classmethod
    def of(cls, **span_data):
        span_type = span_data["type"]
        for subclass in cls.__subclasses__():
            if subclass._type == span_type:
                return subclass(**span_data)
        return ValueError(f"Unknown data type: {span_type}")


class TextSpan(Span):
    _type = "text"

    def __init__(self, **span_data):
        super().__init__(**span_data)

        self.labels = span_data["labels"]


class CrossRefSpan(Span):
    _type = "crossref"

    def __init__(self, **span_data):
        super().__init__(**span_data)

        self.target = span_data["target"]
        self.variant = span_data["variant"]


class BibRefSpan(Span):
    _type = "bibref"

    def __init__(self, **span_data):
        super().__init__(**span_data)

        self.full_reference = span_data["fullReference"]
        self.bib_id = span_data["bibId"]
