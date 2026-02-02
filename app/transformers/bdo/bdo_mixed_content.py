from typing import Union

import pandas as pd

from app.models.annotated_text import (
    BibRefAnnotationSpan,
    CrossRefAnnotationSpan,
    LinkAnnotationSpan,
    TextAnnotationSpan,
)
from app.transformers.standoff.annotation_frame import AnnotationFrame
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


class BdoBaseTransformer(StandoffTransformer):
    @preprocess(order=1)
    def insert_crossref_prefixes(self, aframe: AnnotationFrame) -> AnnotationFrame:
        if "verweis-typ" not in aframe.columns:
            return aframe

        mapped_ref_types = aframe["verweis-typ"].map(REF_TYPE_PREFIXES)

        return (
            aframe.assign(ref_type=mapped_ref_types)
            .insert_attribute("verweis", "ref_type")
            .drop("ref_type", axis=1)
        )

    @register("lemma-form")
    def serialize_mention(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("hoch")
    def serialize_superscript(self, span: pd.Series) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["superscript"])

    @register("verweis")
    def serialize_reference(
        self, span: pd.Series
    ) -> Union[CrossRefAnnotationSpan, LinkAnnotationSpan]:
        if (target := span.get("ziel-extern")) is not None:
            return LinkAnnotationSpan(**basedata(span, "link"), target=target)

        target = span.get("ziel")

        return CrossRefAnnotationSpan(
            **basedata(span, "crossref"),
            variant="arrow" if span.get("verweis-typ") == "Pfeil" else None,
            target="." if target is None else f"/entry/{target}",
        )


class BdoLiteratureTransformer(StandoffTransformer):
    @preprocess(order=1)
    def insert_literature_prefixes(self, aframe: AnnotationFrame) -> AnnotationFrame:
        return aframe.insert_attribute("literatur-quelle", "quelle-art")

    @preprocess(order=3)
    def add_bib_id_column(self, aframe: AnnotationFrame) -> AnnotationFrame:
        bib_spans = aframe.get_spans("literatur-quelle").index

        for span_id in bib_spans:
            subspans = aframe.get_subspans(span_id).index
            aframe.loc[subspans, "bib_id"] = span_id

        return aframe

    @preprocess(order=4)
    def extract_embedded_bibliography(self, aframe: AnnotationFrame) -> AnnotationFrame:
        try:
            return aframe.remove_all_spans(
                "details", remove_subspans=True, remove_text=True
            )
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
            fullReference=details_transformer.serialize(),
        )


class BdoMixedContentTransformer(BdoBaseTransformer, BdoLiteratureTransformer):
    pass
