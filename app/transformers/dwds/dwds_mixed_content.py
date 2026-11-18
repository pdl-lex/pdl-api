from app.models.annotated_text import TextAnnotationSpan
from app.transformers.standoff.character_map import SpanView
from app.transformers.standoff.standoff_transformer import (
    StandoffTransformer,
    register,
    textspan,
)


class DwdsBaseTransformer(StandoffTransformer):
    @register("Stichwort")
    def serialize_stichwort(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["bold"])

    @register("Paraphrase")
    def serialize_paraphrase(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("Autorenzusatz")
    def serialize_autorenzusatz(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("Autor")
    def serialize_autor(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["author"])

    @register("Titel")
    def serialize_titel(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["title"])

    @register("Stelle")
    def serialize_stelle(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["location"])


class DwdsMixedContentTransformer(DwdsBaseTransformer):
    pass
