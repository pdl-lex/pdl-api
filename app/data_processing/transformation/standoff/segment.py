from app.data_processing.transformation.standoff.span import ComparableSpan


class TextSegment(ComparableSpan):
    def __init__(self, start, text):
        self.start = start
        self.text = text
        self.end = self.start + len(text)
        self.labels = set()

    def update_labels(self, additional_labels):
        self.labels.update(additional_labels)

    def to_display(self):
        dump = {"type": "text", "text": self.text}

        if len(self.labels) > 0:
            dump["labels"] = list(self.labels)

        return dump

    def __repr__(self):
        return repr(str(self))


class ContainerSegment(TextSegment):
    _type = "container"

    def __init__(self, text_segment, root_span):
        super().__init__(text_segment.start, text_segment.text)
        self.segments = [text_segment]
        self.root_span = root_span

    @classmethod
    def of(cls, segment, span):
        for subclass in cls.__subclasses__():
            if subclass._type == span.type:
                return subclass(segment, span)
        return cls(segment, span)

    def merge(self, next_segment):
        self.end = next_segment.end
        self.text += next_segment.text
        self.segments.append(next_segment)

    def to_display(self):
        dump = {"type": "_container"}

        return dump


class CrossRefSegment(ContainerSegment):
    _type = "crossref"

    def __init__(self, text_segment, root_span):
        super().__init__(text_segment, root_span)

        self.target = root_span.target
        self.variant = root_span.variant

    def to_display(self):
        return {
            "type": "crossref",
            "text": self.text,
            "target": self.target,
            "variant": self.variant,
            "content": [segment.to_display() for segment in self.segments],
        }


class BibRefSegment(ContainerSegment):
    _type = "bibref"

    def __init__(self, text_segment, root_span):
        super().__init__(text_segment, root_span)

        self.full_reference_data = self.root_span.full_reference
        self.bib_id = self.root_span.bib_id

    def set_full_reference(self, full_reference):
        self.full_reference = full_reference

    def to_display(self):
        dump = {
            "type": "bibref",
            "text": self.text,
            "bib_id": self.bib_id,
            "content": [segment.to_display() for segment in self.segments],
            "detailContent": self.full_reference,
        }

        return dump
