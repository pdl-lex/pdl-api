from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Union

import pandas as pd


class _RootSentinel:
    def __repr__(self):
        return "<ROOT>"


ROOT = _RootSentinel()


def extract_text(row, start, end):
    offset = row.start
    return row.text[: start - offset] + row.text[end - offset :]


def _insert_text(row, position, text):
    offset = row.start
    position -= offset
    return row.text[:position] + text + row.text[position:]


@dataclass(frozen=True)
class AnnotationFrame:
    """
    Immutable container for managing text spans and their hierarchical relationships
    """

    frame: pd.DataFrame
    _deleted_spans: pd.DataFrame = field(default_factory=pd.DataFrame, init=False)

    def __post_init__(self):
        frame = self.frame.copy()
        object.__setattr__(self, "frame", frame)

    @property
    def text(self) -> str:
        return self.get_root().text

    def get_root_id(self) -> str:
        span_sizes = self.frame.end - self.frame.start
        return self.frame.loc[span_sizes.idxmax()].name

    def get_root(self) -> pd.Series:
        return self.get_span(self.get_root_id())

    def get_span(self, tag_id: str) -> pd.Series:
        return self.frame.loc[tag_id]

    def get_spans(self, tag: str) -> pd.DataFrame:
        return self.frame.loc[self.frame.tag == tag]

    def get_subspans(self, tag_id: str, with_root=True) -> "AnnotationFrame":
        start, end = self.frame.loc[tag_id, ["start", "end"]]
        mask = self.frame.start.ge(start) & self.frame.end.le(end)

        return replace(
            self, frame=self.frame[mask] if with_root else self.frame[mask].drop(tag_id)
        )

    def get_superspans(self, tag_id: str, with_root=False) -> "AnnotationFrame":
        start, end = self.frame.loc[tag_id, ["start", "end"]]
        mask = self.frame.start.le(start) & self.frame.end.ge(end)

        return replace(
            self, frame=self.frame[mask] if with_root else self.frame[mask].drop(tag_id)
        )

    def remove_span(self, tag_id: str, remove_text=False) -> "AnnotationFrame":
        to_delete = self.get_subspans(tag_id, with_root=True)
        new_frame = self.frame.drop(to_delete.frame.index)

        if remove_text:
            start, end = self.get_span(tag_id)[["start", "end"]]
            superspans = self.get_superspans(tag_id).frame

            new_frame.loc[superspans.index, "text"] = superspans.apply(
                extract_text,
                start=start,
                end=end,
                axis=1,
            )
            span_size = end - start
            new_frame.loc[superspans.index, "end"] -= span_size
            new_frame.loc[new_frame.start.ge(start), ["start", "end"]] -= span_size

        new_instance = replace(self, frame=new_frame)

        object.__setattr__(
            new_instance,
            "_deleted_spans",
            pd.concat([self._deleted_spans, to_delete.frame]),
        )

        return new_instance

    def remove_all_spans(self, tag: str, remove_text=False) -> "AnnotationFrame":
        new_frame = self.copy()
        tags = self.frame[self.frame.tag == tag].index

        for tag_id in tags:
            new_frame = new_frame.remove_span(tag_id, remove_text=remove_text)

        return new_frame

    def insert_text(
        self,
        position: int,
        text: str,
        parent: Union[str, _RootSentinel] = ROOT,
        relative: bool = False,
    ) -> "AnnotationFrame":
        """
        Insert text at a specific position, updating all affected spans

        Args:
            position: Character position to insert text at
            text: Text to insert
            parent: Span ID to insert within (defaults to root span)
            relative: If True, position is relative to parent span start

        Returns:
            New AnnotationFrame with text inserted and spans adjusted

        Raises:
            IndexError: If position is outside the parent span boundaries
        """
        parent = self.get_root_id() if parent is ROOT else parent
        is_parent = self.frame.index == parent
        parent_span = self.get_span(parent)

        if relative:
            if position < 0:
                position = parent_span.end - parent_span.start + position
            position += parent_span.start

        if not parent_span.start <= position <= parent_span.end:
            raise IndexError(
                f"Position {position} is not within span {parent!r} "
                f"[{parent_span.start}..{parent_span.end}]"
            )

        new_frame = self.frame.copy()

        spans_to_update = self.get_superspans(parent, with_root=True).frame.index
        new_texts = new_frame.loc[spans_to_update].apply(
            _insert_text, axis=1, position=position, text=text
        )
        new_frame.loc[spans_to_update, "text"] = new_texts
        new_frame.loc[spans_to_update, "end"] += len(text)

        trailing_spans = new_frame.start.ge(position) & ~is_parent, ["start", "end"]
        new_frame.loc[trailing_spans] += len(text)

        return replace(self, frame=new_frame)

    def validate(self, debug: bool = False) -> "AnnotationFrame":
        text_by_index = self.frame.apply(
            lambda row: self.text[row.start : row.end], axis=1
        )
        mismatches = text_by_index.ne(self.frame.text)

        if mismatches.any():
            detail = self.frame.text.compare(
                text_by_index, result_names=("stored", "by_index")
            )
            keys = self.frame[mismatches].index.to_list()
            info = f"Found {mismatches.sum()} mismatch(es): {keys}"

            if debug:
                print(info)
                return detail

            raise ValueError(f"{info}\n\n{detail}")
        elif debug:
            print("All clear!")

        return self

    def _repr_html_(self):
        return self.frame._repr_html_()

    def __repr__(self) -> str:
        return repr(self.frame)

    def copy(self) -> "AnnotationFrame":
        return deepcopy(self)
