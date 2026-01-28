from typing import Optional, Union

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


class AnnotationFrame(pd.DataFrame):
    _metadata = ["_deleted_spans"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._deleted_spans = pd.DataFrame()

    def __finalize__(self, other, method=None, **kwargs):
        """Propagate metadata from other to self"""
        self = super().__finalize__(other, method, **kwargs)
        if hasattr(other, "_deleted_spans"):
            self._deleted_spans = other._deleted_spans
        return self

    @property
    def _constructor(self):
        return AnnotationFrame

    @property
    def _constructor_sliced(self):
        return pd.Series

    @property
    def _roottext(self) -> str:
        return self.get_root().text

    def get_root_id(self) -> str:
        span_sizes = self.end - self.start
        return self.loc[span_sizes.idxmax()].name

    def get_root(self) -> pd.Series:
        return self.get_span(self.get_root_id())

    def get_span(self, tag_id: str) -> pd.Series:
        return self.loc[tag_id]

    def get_spans(self, tag: str) -> pd.DataFrame:
        return self.loc[self.tag == tag]

    def get_first(self, tag: str) -> pd.Series:
        return self.get_spans(tag).iloc[0]

    def get_subspans(self, tag_id: str, with_root=True) -> "AnnotationFrame":
        start, end = self.loc[tag_id, ["start", "end"]]
        mask = self.start.ge(start) & self.end.le(end)

        return self[mask] if with_root else self[mask].drop(tag_id)

    def get_superspans(self, tag_id: str, with_root=False) -> "AnnotationFrame":
        start, end = self.loc[tag_id, ["start", "end"]]
        mask = self.start.le(start) & self.end.ge(end)

        return self[mask] if with_root else self[mask].drop(tag_id)

    def remove_span(self, tag_id: str, remove_text=False) -> "AnnotationFrame":
        to_delete = self.get_subspans(tag_id, with_root=True)
        new_frame = self.copy().drop(to_delete.index)

        if remove_text:
            start, end = self.get_span(tag_id)[["start", "end"]]
            superspans = self.get_superspans(tag_id)

            new_frame.loc[superspans.index, "text"] = superspans.apply(
                extract_text,
                start=start,
                end=end,
                axis=1,
            )
            span_size = end - start
            new_frame.loc[superspans.index, "end"] -= span_size
            new_frame.loc[new_frame.start.ge(start), ["start", "end"]] -= span_size

        new_frame._deleted_spans = pd.concat([self._deleted_spans, to_delete.frame])

        return new_frame

    def remove_all_spans(self, tag: str, remove_text=False) -> "AnnotationFrame":
        new_frame = self.copy()
        tags = self[self.tag == tag].index

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
        is_parent = self.index == parent
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

        new_frame = self.copy()

        spans_to_update = [
            *self.loc[self.start.lt(position) & self.end.gt(position)].index,
            parent,
        ]

        new_texts = new_frame.loc[spans_to_update].apply(
            _insert_text, axis=1, position=position, text=text
        )
        new_frame.loc[spans_to_update, "text"] = new_texts
        new_frame.loc[spans_to_update, "end"] += len(text)

        trailing_spans = new_frame.start.ge(position) & ~is_parent, ["start", "end"]
        new_frame.loc[trailing_spans] += len(text)

        return new_frame

    def validate(self, debug: bool = False) -> "AnnotationFrame":
        text_by_index = self.apply(
            lambda row: self._roottext[row.start : row.end], axis=1
        )
        mismatches = text_by_index.ne(self.text)

        if mismatches.any():
            detail = self.text.compare(
                text_by_index, result_names=("stored", "by_index")
            )
            keys = self[mismatches].index.to_list()
            info = f"Found {mismatches.sum()} mismatch(es): {keys}"

            if debug:
                print(info)
                return detail

            raise ValueError(f"{info}\n\n{detail}")
        elif debug:
            print("All clear!")

        return self

    def add_attribute(self, name: str, values: pd.Series):
        new_frame = self.assign(**{name: values})
        return new_frame

    def iter_spans(self, tag: Optional[str] = None):
        frame = self if tag is None else self.get_spans(tag)
        for _, span in frame.iterrows():
            yield span

    def normalize_offsets(self):
        offset = self.start.min()
        new_frame = self.copy()
        new_frame.loc[:, ["start", "end"]] -= offset

        return new_frame
