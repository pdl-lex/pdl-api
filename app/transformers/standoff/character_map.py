"""Standoff representation of mixed content: a plain text plus [start, end) spans.

Every edit (insert, replace, delete) updates the text and shifts the span offsets
accordingly, so spans always stay aligned with the text.
"""

from dataclasses import dataclass
from itertools import accumulate
from typing import Any


class SpanNotFoundError(Exception):
    pass


@dataclass(slots=True)
class Span:
    span_id: str
    tag: str
    depth: int
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SpanView:
    """Read-only snapshot of a span, as passed to transformer handlers."""

    span_id: str
    tag: str
    depth: int
    start: int
    end: int
    text: str
    attributes: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.attributes[key]

    def __contains__(self, key: str) -> bool:
        return key in self.attributes


class CharacterMap:
    def __init__(
        self,
        text: str,
        spans: list[Span],
        span_attributes: dict[str, dict[str, Any]] | None = None,
    ):
        self._text = text
        self._spans = spans
        self.span_attributes = {} if span_attributes is None else span_attributes

    @property
    def text(self) -> str:
        return self._text

    def _find(self, span_id: str) -> Span | None:
        return next((s for s in self._spans if s.span_id == span_id), None)

    def _remap(self, text: str, position_map: list[int]) -> None:
        """Replace the text, move span offsets via old->new positions, drop empty spans."""
        for span in self._spans:
            span.start = position_map[span.start]
            span.end = position_map[span.end]
        self._spans = [s for s in self._spans if s.start < s.end]
        self._text = text

    def _keep(self, keep: list[bool]) -> None:
        text = "".join(c for c, k in zip(self._text, keep, strict=True) if k)
        self._remap(text, [0, *accumulate(keep)])

    def normalize_ws(self) -> "CharacterMap":
        """Replace whitespace by spaces and merge consecutive spaces."""
        self._text = "".join(" " if c.isspace() else c for c in self._text)
        self._keep(
            [
                not (c == " " and i > 0 and self._text[i - 1] == " ")
                for i, c in enumerate(self._text)
            ]
        )
        return self

    def minify(self) -> "CharacterMap":
        """
        Normalize whitespace and move leading and trailing whitespace within spans into
        parent spans. E.g., transforms

        `<outer>  <inner> foo </inner>  <inner>  bar  </inner>  </outer>`

        into

        `<outer><inner>foo</inner> <inner>bar</inner></outer>`.
        """
        self.normalize_ws()
        text = self._text

        for span in self._spans:
            if text[span.start] == " ":
                span.start += 1
            if span.start < span.end and text[span.end - 1] == " ":
                span.end -= 1
        self._spans = [s for s in self._spans if s.start < s.end]

        coverage = [0] * (len(text) + 1)
        for span in self._spans:
            coverage[span.start] += 1
            coverage[span.end] -= 1
        covered = list(accumulate(coverage))

        self._keep([c != " " or covered[i] > 0 for i, c in enumerate(text)])
        return self

    def insert(
        self, index: int, text: str, host_span: str | None = None
    ) -> "CharacterMap":
        """
        Insert text at index. The text becomes part of the root and of all spans that
        strictly contain the index. If host_span starts or ends at the index, the host
        and its ancestors sharing that boundary are extended to include the text.
        """
        n = len(text)
        if n == 0:
            return self

        host = None
        if host_span is not None:
            host = self._find(host_span)
            if host is None:
                raise SpanNotFoundError(f"Span {host_span!r} not found")
            if host.depth == 0:
                host = None

        extend_left = host is not None and host.end == index
        extend_right = host is not None and not extend_left and host.start == index

        for span in self._spans:
            if span.depth == 0 or span.start < index < span.end:
                span.end += n
            elif span.end <= index:
                if extend_left and span.end == index and span.depth <= host.depth:
                    span.end += n
            elif extend_right and span.start == index and span.depth <= host.depth:
                span.end += n
            else:
                span.start += n
                span.end += n

        self._text = self._text[:index] + text + self._text[index:]
        return self

    def set_text(self, span_id: str, text: str) -> "CharacterMap":
        """
        Replace the text of a span. Subspans starting at the span's first character
        cover the new text; all other subspans are discarded.
        """
        target = self._find(span_id)
        if len(text) == 0 or target is None:
            return self

        a, b = target.start, target.end
        delta = len(text) - (b - a)

        for span in self._spans:
            if span.end <= a:
                continue
            if span.start >= b:
                span.start += delta
                span.end += delta
            elif span.start <= a:
                span.end = max(span.end, b) + delta
            elif span.end > b:
                span.start = a + len(text)
                span.end += delta
            else:
                span.end = span.start

        self._spans = [s for s in self._spans if s.start < s.end]
        self._text = self._text[:a] + text + self._text[b:]
        return self

    def pop_span(self, span_id: str) -> "CharacterMap":
        """Cut out the characters of a span and return them as a new map."""
        attributes = dict(self.span_attributes)
        target = self._find(span_id)
        if target is None:
            return CharacterMap("", [], attributes)

        a, b = target.start, target.end
        submap = CharacterMap(
            self._text[a:b],
            [
                Span(s.span_id, s.tag, s.depth, max(s.start, a) - a, min(s.end, b) - a)
                for s in self._spans
                if s.start < b and s.end > a
            ],
            attributes,
        )

        n = b - a
        self._remap(
            self._text[:a] + self._text[b:],
            [p if p <= a else max(a, p - n) for p in range(len(self._text) + 1)],
        )

        return submap

    def get_span_range(self, span_id: str) -> tuple[int, int]:
        span = self._find(span_id)
        if span is None:
            raise SpanNotFoundError(f"Span {span_id!r} not found")
        return span.start, span.end

    def spans(self, tag: str | None = None) -> list[str]:
        """Span ids in text order, optionally filtered by tag."""
        ordered = sorted(self._spans, key=lambda s: (s.start, s.depth))
        return [s.span_id for s in ordered if tag is None or s.tag == tag]

    def get_subspans(self, span_id: str) -> list[str]:
        target = self._find(span_id)
        if target is None:
            return []
        return [
            s.span_id
            for s in self._spans
            if s is not target
            and s.depth >= target.depth
            and s.start < target.end
            and s.end > target.start
        ]

    def add_span(
        self,
        tag: str,
        start: int,
        end: int,
        attributes: dict[str, Any] | None = None,
    ) -> "CharacterMap":
        """Add a span on the shallowest layer that is free within [start, end)."""
        in_use = {int(s.span_id.rsplit("_", 1)[1]) for s in self._spans if s.tag == tag}
        index = next(i for i in range(1, len(in_use) + 2) if i not in in_use)
        span_id = f"{tag}_{index}"
        self.span_attributes[span_id] = {} if attributes is None else attributes

        occupied = {s.depth for s in self._spans if s.start < end and s.end > start}
        depth = next(d for d in range(len(occupied) + 1) if d not in occupied)
        self._spans.append(Span(span_id, tag, depth, start, end))

        return self

    def rename_tag(self, tag: str, value: str) -> "CharacterMap":
        for span in self._spans:
            if span.tag != tag:
                continue
            old_id = span.span_id
            span.tag = value
            span.span_id = f"{value}_{old_id.rsplit('_', 1)[1]}"
            if old_id in self.span_attributes:
                self.span_attributes[span.span_id] = self.span_attributes.pop(old_id)
        return self

    def to_spans(self) -> list[SpanView]:
        """All spans in canonical order (depth, start)."""
        ordered = sorted(self._spans, key=lambda s: (s.depth, s.start, s.span_id))
        return [
            SpanView(
                span_id=s.span_id,
                tag=s.tag,
                depth=s.depth,
                start=s.start,
                end=s.end,
                text=self._text[s.start : s.end],
                attributes=self.span_attributes.get(s.span_id, {}),
            )
            for s in ordered
        ]

    def __repr__(self) -> str:
        return f"CharacterMap({self._text!r}, {self._spans!r})"
