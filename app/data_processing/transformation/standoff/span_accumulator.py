from typing import Optional, Sequence

from app.data_processing.transformation.standoff.segment import (
    BibRefSegment,
    ContainerSegment,
    TextSegment,
)
from app.data_processing.transformation.standoff.span import Span


class SpanAccumulator:
    def __init__(self, data):
        self.text = data["text"]
        self.spans = [Span.of(**item) for item in data["annotations"]]
        self.segments = self._init_segments()

    def get_spans(self, only: Optional[Sequence]):
        return [span for span in self.spans if only is None or span.type in only]

    def spans_in_range(self, other, only=None):
        for span in self.get_spans(only):
            if span.has_overlap(other.start, other.end):
                yield span

    def apply_annotations(self, segment):
        for span in self.spans_in_range(segment, only=["text"]):
            segment.update_labels(span.labels)

        return segment

    def _init_segments(self):
        segments = []
        text = self.text

        breaks = sorted(
            {index for span in self.spans for index in [span.start, span.end]} | {0},
            reverse=True,
        )
        for index in breaks:
            segment = TextSegment(index, text[index:])
            segment = self.apply_annotations(segment)
            segments.append(segment)
            text = text[:index]

        return list(reversed(segments))

    def iter_segments(self, only=None):
        """Iterate over segments with their corresponding spans"""
        for segment in self.segments:
            yield (segment, list(self.spans_in_range(segment, only=only)))

    def accumulate_segments(self):
        for segment, c_spans in self.iter_segments(only=["bibref", "crossref"]):
            if len(c_spans) == 0:
                yield segment
                continue

            c_span = c_spans[0]

            if segment.start == c_span.start:
                current_container = ContainerSegment.of(segment, c_span)

                if isinstance(current_container, BibRefSegment):
                    full_reference = SpanAccumulator(
                        current_container.full_reference_data
                    ).to_display()
                    current_container.set_full_reference(full_reference)
            else:
                current_container.merge(segment)

            if segment.end == c_span.end:
                yield current_container

    def to_display(self):
        return {
            "text": self.text,
            "spans": [segment.to_display() for segment in self.accumulate_segments()],
        }
