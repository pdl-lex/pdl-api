from typing import Callable

import pandas as pd

from app.transformers.standoff.character_map import CharacterMap


def xml_to_standoff(node, offset=0, depth=0, spans=None, basetext=None):
    if spans is None:
        spans = []

    full_text = "".join(node.itertext())
    basetext = full_text if basetext is None else basetext
    end = offset + len(full_text)

    markable = (offset, end, depth, node.tag, node.attrib, basetext[offset:end])
    spans.append(markable)

    offset += len(node.text or "")

    for subnode in node:
        if not isinstance(subnode.tag, str):
            continue
        xml_to_standoff(subnode, offset, depth + 1, spans, basetext)
        offset += len("".join(subnode.itertext())) + len(subnode.tail or "")

    return spans


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


def textspan(span):
    return basedata(span, "text")


def parse_attributes(frame: pd.DataFrame) -> pd.DataFrame:
    attributes = pd.DataFrame.from_records(frame["attributes"])
    frame = frame.drop("attributes", axis=1)

    return pd.concat([frame, attributes], axis=1)


def add_span_ids(frame: pd.DataFrame) -> pd.DataFrame:
    tag_counters = frame.groupby("tag").cumcount() + 1
    ids = frame.tag + "_" + tag_counters.astype(str)

    return frame.assign(span_id=ids)


class StandoffTransformer:
    def __init__(self, cmap: CharacterMap):
        self.cmap = cmap
        self._tag_handlers = self._collect_tag_handlers()
        self._apply_preprocessing()
        self.errors = []

    @classmethod
    def load_xml(cls, xml_node) -> "StandoffTransformer":
        span_data = xml_to_standoff(xml_node)

        frame = pd.DataFrame(
            span_data,
            columns=["start", "end", "depth", "tag", "attributes", "text"],
        )
        frame = parse_attributes(frame)
        frame = add_span_ids(frame)
        cmap = CharacterMap.from_spans(frame).minify()

        return cls(cmap)

    @classmethod
    def from_cmap(cls, cmap: CharacterMap):
        return cls(cmap)

    def _apply_preprocessing(self):
        """Apply all methods decorated with @preprocess to self.cmap"""
        preprocess_methods = []

        for cls in type(self).__mro__:
            for name, method in cls.__dict__.items():
                if callable(method) and hasattr(method, "_is_preprocess"):
                    priority = getattr(method, "_preprocess_priority", 0)
                    preprocess_methods.append((priority, name, method))

        preprocess_methods.sort(key=lambda m: (m[0], m[1]))

        for *_, method in preprocess_methods:
            self.cmap = method(self, self.cmap)

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
        self.cmap = self.cmap.minify()
        result = {"text": self.cmap.text, "annotations": self._serialize_spans()}
        return result
