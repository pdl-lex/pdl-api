from typing import Union

import pandas as pd

from app.models.annotated_text import (
    AnnotatedTextData,
    BibRefAnnotationSpan,
    CrossRefAnnotationSpan,
    LinkAnnotationSpan,
    TextAnnotationSpan,
)
from app.transformers.standoff.character_map import CharacterMap
from app.transformers.standoff.standoff_transformer import (
    StandoffTransformer,
    basedata,
    preprocess,
    register,
    textspan,
)

REF_TYPE_PREFIXES = {
    None: "",
    "Pfeil": "",
    "ohne": "",
    "siehe": "siehe ",
    "siehe-auch": "siehe auch ",
    "vgl.": "vgl. ",
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
    def insert_crossref_prefixes(self, cmap: CharacterMap) -> CharacterMap:
        spans = cmap.to_spans()

        for _, span in spans[spans.tag == "verweis"].iterrows():
            # insert the verweis-typ into the base text
            insertion = REF_TYPE_PREFIXES.get(span.get("verweis-typ"), "")
            cmap = cmap.insert(span.start, insertion)

            if span.get("ziel-typ") == "Bedeutung":
                # get nested lemma-referenz
                lemma_refs = spans[
                    spans.tag.eq("lemma-referenz")
                    & spans.start.ge(span.start)
                    & spans.end.le(span.end)
                ]
                if len(lemma_refs) == 0:
                    continue

                lemma_ref_span = lemma_refs.iloc[0]

                if "vollform" not in lemma_ref_span:
                    continue

                # expand full lemma
                full_lemma = lemma_ref_span["vollform"] + ", "
                cmap.set_text(lemma_ref_span.span_id, full_lemma)

                # insert "Bed. " text
                cmap = cmap.insert(
                    cmap.get_span_range(lemma_ref_span.span_id)[1],
                    "Bed. ",
                    span.span_id,
                )

        return cmap.reset_index()

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

    @register("kompositum")
    def serialize_compound(
        self, span: pd.Series
    ) -> Union[CrossRefAnnotationSpan, LinkAnnotationSpan]:
        """Kompositum-nodes share the structure of verweis-nodes"""
        return self.serialize_reference(span)


class BdoLiteratureTransformer(StandoffTransformer):
    def set_bibliography_details(self, submap: CharacterMap) -> None:
        self._bibliography = submap.reset_index()

    def get_bibliography_details(self) -> CharacterMap | None:
        return getattr(self, "_bibliography", None)

    @preprocess(order=1)
    def insert_literature_prefixes(self, cmap: CharacterMap) -> CharacterMap:
        for span_id in cmap.spans("literatur-quelle"):
            start, _ = cmap.get_span_range(span_id)
            attributes = cmap.span_attributes[span_id]

            cmap = cmap.insert(start, attributes.get("quelle-art", "") + " ")

        return cmap.reset_index()

    @preprocess(order=3)
    def add_bib_id_column(self, cmap: CharacterMap) -> CharacterMap:
        for span_id in cmap.spans("literatur-quelle"):
            for subspan in cmap.get_subspans(span_id):
                if subspan not in cmap.span_attributes:
                    cmap.span_attributes[subspan] = {}
                cmap.span_attributes[subspan]["bib_id"] = span_id

        return cmap

    @preprocess(order=4)
    def extract_embedded_bibliography(self, cmap: CharacterMap) -> CharacterMap:
        for span_id in cmap.spans("details"):
            self.set_bibliography_details(cmap.pop_span(span_id))

        return cmap.reset_index()

    @register("literatur-quelle")
    def serialize_bibref(self, span) -> Union[BibRefAnnotationSpan, None]:
        details = self.get_bibliography_details()

        if details is None:
            return None

        details_transformer = BdoBaseTransformer.from_cmap(details)

        return BibRefAnnotationSpan(
            **basedata(span, "bibref"),
            bibId=span.fillna("").get("literatur", ""),
            fullReference=AnnotatedTextData(**details_transformer.serialize()),
        )


class BdoMixedContentTransformer(BdoBaseTransformer, BdoLiteratureTransformer):
    pass
