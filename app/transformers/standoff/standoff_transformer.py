from typing import Any, Callable

import pandas as pd

from app.transformers.standoff.annotation_frame import AnnotationFrame, Padding
from app.transformers.standoff.character_map import CharacterMap
from app.transformers.standoff.xml_standoff_converter import (
    xml_to_standoff,
)


def preprocess(func_or_priority=None, *, order: int = 0):
    """Decorator to mark methods as preprocessing steps with optional priority"""

    def decorator(func: Callable) -> Callable:
        func._is_preprocess = True
        func._preprocess_priority = order
        return func

    if callable(func_or_priority):
        return decorator(func_or_priority)

    return decorator


def register(tag: str):
    """Decorator to register methods for specific annotation tags"""

    def decorator(func: Callable) -> Callable:
        func._registered_tag = tag
        return func

    return decorator


def basedata(span, type_: str) -> dict:
    return {"type": type_, **span[["start", "end", "text"]].to_dict()}


class StandoffTransformer:
    def __init__(self, aframe: AnnotationFrame, cmap: CharacterMap):
        self.aframe = aframe
        self.cmap = cmap
        self._tag_handlers = self._collect_tag_handlers()
        self._apply_preprocessing()
        self.errors = []

    @classmethod
    def load_xml(cls, xml_node) -> "StandoffTransformer":
        span_data = xml_to_standoff(xml_node)
        aframe = AnnotationFrame(cls._init_dataframe(span_data))
        cmap = CharacterMap.from_spans(aframe)
        return cls(aframe, cmap)

    @classmethod
    def _init_dataframe(cls, span_data: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(
            span_data, columns=["start", "end", "depth", "tag", "_attributes", "text"]
        )
        extra_attributes = pd.DataFrame.from_records(frame.pop("_attributes"))
        frame = pd.concat([frame, extra_attributes], axis=1)

        frame = cls._add_unique_ids(frame)

        return frame

    @staticmethod
    def _add_unique_ids(frame: pd.DataFrame) -> pd.DataFrame:
        tag_counters = frame.groupby("tag").cumcount() + 1
        ids = frame.tag + "_" + tag_counters.astype(str)

        return frame.assign(span_id=ids).set_index("span_id")

    def _apply_preprocessing(self):
        """Apply all methods decorated with @preprocess to self.aframe"""
        preprocess_methods = []

        for cls in type(self).__mro__:
            for name, method in cls.__dict__.items():
                if callable(method) and hasattr(method, "_is_preprocess"):
                    priority = getattr(method, "_preprocess_priority", 0)
                    preprocess_methods.append((priority, name, method))

        preprocess_methods.sort(key=lambda m: (m[0], m[1]))

        for *_, method in preprocess_methods:
            self.aframe, self.cmap = method(self, self.aframe, self.cmap)

    def _collect_tag_handlers(self) -> dict[str, Callable]:
        """Collect all methods decorated with @register"""
        handlers = {}

        for cls in type(self).__mro__:
            for _, method in cls.__dict__.items():
                if callable(method) and hasattr(method, "_registered_tag"):
                    tag = method._registered_tag
                    if tag not in handlers:
                        handlers[tag] = method

        return handlers

    def _serialize_spans(self) -> list[dict]:
        """Transform spans by dispatching to registered tag handlers"""
        serialized_spans = []
        spans = self.cmap.to_spans()

        for _, span in spans.iterrows():
            tag = span.tag
            if tag in self._tag_handlers:
                handler = self._tag_handlers[tag]
                try:
                    result = handler(self, span)
                except Exception as err:
                    self.errors.append((span.tag, str(err)))
                    result = None

                if result is not None:
                    serialized_spans.append(result.model_dump(by_alias=True))

        return serialized_spans

    def serialize(self) -> dict:
        result = {"text": self.aframe._roottext, "annotations": self._serialize_spans()}
        return result
