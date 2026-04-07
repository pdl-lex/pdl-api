import pandas as pd

from app.models.annotated_text import TextAnnotationSpan
from app.transformers.standoff.standoff_transformer import (
    StandoffTransformer,
    register,
)


def basedata(span, type_: str) -> dict:
    return {"type": type_, **span[["start", "end", "text"]].to_dict()}


def textspan(span):
    return basedata(span, "text")


class DwdsBaseTransformer(StandoffTransformer):
    @register("Stichwort")
    def serialize_stichwort(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["bold"])

    @register("Paraphrase")
    def serialize_paraphrase(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("Autorenzusatz")
    def serialize_autorenzusatz(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("Autor")
    def serialize_autor(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["author"])

    @register("Titel")
    def serialize_titel(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["title"])

    @register("Stelle")
    def serialize_stelle(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["location"])


class DwdsMixedContentTransformer(DwdsBaseTransformer):
    pass
