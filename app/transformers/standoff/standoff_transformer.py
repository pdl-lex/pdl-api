from functools import cache
from typing import Callable

from app.transformers.standoff.character_map import CharacterMap, Span, SpanView


def xml_to_standoff(node, offset=0, depth=0, spans=None, basetext=None):
    if spans is None:
        spans = []

    full_text = "".join(node.itertext())
    basetext = full_text if basetext is None else basetext
    end = offset + len(full_text)

    markable = [offset, end, depth, node.tag, dict(node.attrib), basetext[offset:end]]
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


def basedata(span: SpanView, type_: str) -> dict:
    return {"type": type_, "start": span.start, "end": span.end, "text": span.text}


def textspan(span: SpanView) -> dict:
    return basedata(span, "text")


def character_map_from_xml(xml_node) -> CharacterMap:
    """Build a CharacterMap with span ids `<tag>_<n>`, numbered in document order."""
    counters: dict[str, int] = {}
    text, spans, attributes = "", [], {}

    for start, end, depth, tag, attrib, span_text in xml_to_standoff(xml_node):
        counters[tag] = counters.get(tag, 0) + 1
        span_id = f"{tag}_{counters[tag]}"
        if start >= end:
            continue
        if depth == 0:
            text = span_text
        spans.append(Span(span_id, tag, depth, start, end))
        attributes[span_id] = attrib

    return CharacterMap(text, spans, attributes)


@cache
def _collect_methods(cls: type) -> tuple[dict[str, Callable], list[Callable]]:
    """Collect @register handlers and @preprocess steps; subclasses override by name."""
    handlers: dict[str, Callable] = {}
    preprocessors: dict[str, tuple[int, Callable]] = {}

    for klass in reversed(cls.__mro__):
        for name, attr in vars(klass).items():
            if not callable(attr):
                continue
            if hasattr(attr, "_registered_tag"):
                handlers[attr._registered_tag] = attr
            if hasattr(attr, "_is_preprocess"):
                preprocessors[name] = (attr._preprocess_priority, attr)

    ordered = sorted(preprocessors.items(), key=lambda item: (item[1][0], item[0]))
    return handlers, [method for _, (_, method) in ordered]


class StandoffTransformer:
    def __init__(self, cmap: CharacterMap):
        self.cmap = cmap
        self.errors = []
        self._tag_handlers, preprocessors = _collect_methods(type(self))

        for method in preprocessors:
            self.cmap = method(self, self.cmap)

    @classmethod
    def load_xml(cls, xml_node) -> "StandoffTransformer":
        return cls(character_map_from_xml(xml_node))

    @classmethod
    def from_cmap(cls, cmap: CharacterMap) -> "StandoffTransformer":
        return cls(cmap)

    def _serialize_spans(self) -> list[dict]:
        """Transform spans by dispatching to registered tag handlers"""
        serialized_spans = []

        for span in self.cmap.to_spans():
            handler = self._tag_handlers.get(span.tag)
            if handler is None:
                continue
            try:
                result = handler(self, span)
            except Exception as err:
                self.errors.append((span.tag, str(err)))
                continue
            if result is not None:
                serialized_spans.append(result.model_dump(by_alias=True))

        return serialized_spans

    def serialize(self) -> dict:
        self.cmap = self.cmap.minify()
        return {"text": self.cmap.text, "annotations": self._serialize_spans()}
