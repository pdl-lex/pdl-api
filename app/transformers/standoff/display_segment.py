from abc import ABC, abstractmethod

from app.models.annotated_text_display import (
    AnnotatedTextDisplay,
    BibRefDisplay,
    CrossRefDisplay,
    LinkDisplay,
    TextDisplay,
)
from app.transformers.standoff.span import ComparableSpan


class TextSegment(ComparableSpan):
    def __init__(self, start, text):
        self.start = start
        self.text = text
        self.end = self.start + len(text)
        self.labels = set()

    def update_labels(self, additional_labels):
        self.labels.update(additional_labels)

    def to_display(self) -> TextDisplay:
        dump = {"type": "text", "text": self.text}

        if len(self.labels) > 0:
            dump["labels"] = list(self.labels)

        return dump


class ContainerSegment(ABC, TextSegment):
    _type = "container"

    def __init__(self, span):
        super().__init__(span.start, span.text)
        self.segments = []

    def __new__(cls, span):
        if cls is ContainerSegment:
            for subclass in cls.__subclasses__():
                if subclass._type == span.type:
                    return super(ContainerSegment, subclass).__new__(subclass)
        return super().__new__(cls)

    def push_segment(self, segment):
        self.segments.append(segment)

        return self

    @abstractmethod
    def to_display(self): ...


class LinkSegment(ContainerSegment):
    _type = "link"

    def __init__(self, span):
        super().__init__(span)

        self.target = span.target

    def to_display(self) -> LinkDisplay:
        return {
            "type": "link",
            "text": self.text,
            "target": self.target,
            "content": [segment.to_display() for segment in self.segments],
        }


class CrossRefSegment(ContainerSegment):
    _type = "crossref"

    def __init__(self, span):
        super().__init__(span)

        self.target = span.target
        self.variant = span.variant

    def to_display(self) -> CrossRefDisplay:
        return {
            "type": "crossref",
            "text": self.text,
            "target": self.target,
            "variant": self.variant,
            "content": [segment.to_display() for segment in self.segments],
        }


class BibRefSegment(ContainerSegment):
    _type = "bibref"

    def __init__(self, span):
        super().__init__(span)

        self.full_reference_data = span.full_reference
        self.bib_id = span.bib_id

    def set_full_reference(self, full_reference: AnnotatedTextDisplay):
        self.full_reference = full_reference
        return self

    def to_display(self) -> BibRefDisplay:
        dump = {
            "type": "bibref",
            "text": self.text,
            "bibId": self.bib_id,
            "content": [segment.to_display() for segment in self.segments],
            "fullReference": self.full_reference,
        }

        return dump
