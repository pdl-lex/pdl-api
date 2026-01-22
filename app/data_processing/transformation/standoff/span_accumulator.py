from typing import Optional, Sequence

from app.data_processing.transformation.standoff.segment import (
    BibRefSegment,
    ContainerSegment,
    TextSegment,
)
from app.data_processing.transformation.standoff.span import Span
from app.models.span_annotation import AnnotatedTextDisplay


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

    def _init_segments(self) -> list[TextSegment]:
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

    def get_containers(self, segment):
        return list(self.spans_in_range(segment, only=["bibref", "crossref"]))

    def _init_container(self, span):
        container = ContainerSegment(span)

        if isinstance(container, BibRefSegment):
            full_reference = SpanAccumulator(container.full_reference_data).to_display()
            return container.set_full_reference(full_reference)
        else:
            return container

    def accumulate_segments(self):
        container = None

        for segment in self.segments:
            containers = self.get_containers(segment)

            if len(containers) > 0 and container is None:
                container = self._init_container(containers[0])

            if container is None:
                yield segment
            else:
                container.push_segment(segment)

                if container.end == segment.end:
                    yield container
                    container = None

    def to_display(self) -> AnnotatedTextDisplay:
        return {
            "text": self.text,
            "spans": [segment.to_display() for segment in self.accumulate_segments()],
        }
