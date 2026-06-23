from typing import Union

import pandas as pd

from app.models.annotated_text import (
    AnnotatedTextData,
    BibRefAnnotationSpan,
    CrossRefAnnotationSpan,
    LinkAnnotationSpan,
    TextAnnotationSpan,
)
from app.transformers.standoff.annotation_frame import AnnotationFrame
from app.transformers.standoff.character_map import CharacterMap
from app.transformers.standoff.standoff_transformer import (
    StandoffTransformer,
    preprocess,
    register,
)


def basedata(span, type_: str) -> dict:
    return {"type": type_, **span[["start", "end", "text"]].to_dict()}


def textspan(span):
    return basedata(span, "text")


REF_TYPE_PREFIXES = {
    None: "",
    "Pfeil": "",
    "ohne": "",
    "siehe": "siehe",
    "siehe-auch": "siehe auch",
    "vgl.": "vgl.",
}


def get_target_link(span):
    target_type = span.get("ziel-typ")
    base_url = "/search?lemma={}"

    match target_type:
        case "Lemma":
            return base_url.format(span["ziel"])
        case "Bedeutung":
            lemma_id = span["ziel"].rsplit("_", maxsplit=1)[0]
            return base_url.format(lemma_id)
        case _:
            return "."


class BdoBaseTransformer(StandoffTransformer):
    @preprocess(order=1)
    def insert_crossref_prefixes(
        self, aframe: AnnotationFrame, cmap: CharacterMap
    ) -> AnnotationFrame:
        for span_id in cmap.spans("verweis"):
            start, _ = cmap.get_span_range(span_id)
            attributes = cmap.span_attributes[span_id]

            insertion = REF_TYPE_PREFIXES[attributes.get("verweis-typ")]
            cmap = cmap.insert(start, insertion)

        return aframe, cmap.reset_index()

    @preprocess
    def rename_compounds(
        self, aframe: AnnotationFrame, cmap: CharacterMap
    ) -> AnnotationFrame:
        return aframe, cmap.rename_tag("kompositum", "verweis")

    @register("lemma-form")
    def serialize_mention(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("hoch")
    def serialize_superscript(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["superscript"])

    @register("beleg-text")
    def serialize_example(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("verweis")
    def serialize_reference(
        self, span: pd.Series
    ) -> Union[CrossRefAnnotationSpan, LinkAnnotationSpan]:
        if (external := span.get("ziel-extern")) is not None:
            return LinkAnnotationSpan(**basedata(span, "link"), target=external)

        return CrossRefAnnotationSpan(
            **basedata(span, "crossref"),
            variant="arrow" if span.get("verweis-typ") == "Pfeil" else None,
            target=get_target_link(span),
            missing=span.get("fehlt") == "ja",
        )


class BdoLiteratureTransformer(StandoffTransformer):
    @preprocess(order=1)
    def insert_literature_prefixes(
        self, aframe: AnnotationFrame, cmap: CharacterMap
    ) -> AnnotationFrame:
        return self.pluck_attribute(
            aframe, "literatur-quelle", "quelle-art", padding="right"
        ), cmap

    @preprocess(order=3)
    def add_bib_id_column(
        self, aframe: AnnotationFrame, cmap: CharacterMap
    ) -> AnnotationFrame:
        bib_spans = aframe.get_spans("literatur-quelle").index

        for span_id in bib_spans:
            subspans = aframe.get_subspans(span_id).index
            aframe.loc[subspans, "bib_id"] = span_id

        return aframe, cmap

    @preprocess(order=4)
    def extract_embedded_bibliography(
        self, aframe: AnnotationFrame, cmap: CharacterMap
    ) -> AnnotationFrame:
        try:
            return aframe.remove_all_spans(
                "details", remove_subspans=True, remove_text=True
            ), cmap
        except Exception as err:
            print("Could not handle")
            print(aframe)
            print()
            raise err

    @register("literatur-quelle")
    def serialize_bibref(self, span) -> Union[BibRefAnnotationSpan, None]:
        details = self.aframe._deleted_spans

        if details is None:
            return None

        details_transformer = BdoBaseTransformer(
            details[details.bib_id == span.name].normalize_offsets()
        )

        return BibRefAnnotationSpan(
            **basedata(span, "bibref"),
            bibId=span.fillna("").get("literatur", ""),
            fullReference=AnnotatedTextData(**details_transformer.serialize()),
        )


class BdoMixedContentTransformer(BdoBaseTransformer, BdoLiteratureTransformer):
    pass
