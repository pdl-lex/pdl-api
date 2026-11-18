from typing import Union

from app.models.annotated_text import (
    AnnotatedTextData,
    BibRefAnnotationSpan,
    CrossRefAnnotationSpan,
    LinkAnnotationSpan,
    TextAnnotationSpan,
)
from app.transformers.standoff.character_map import CharacterMap, SpanView
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
        for reference in cmap.spans("verweis"):
            attributes = cmap.span_attributes[reference]

            # insert the verweis-typ into the base text
            insertion = REF_TYPE_PREFIXES.get(attributes.get("verweis-typ"), "")
            cmap = cmap.insert(cmap.get_span_range(reference)[0], insertion)

            if attributes.get("ziel-typ") == "Bedeutung":
                lemma_refs = cmap.get_subspans(reference, tag="lemma-referenz")
                if len(lemma_refs) == 0:
                    continue

                lemma_ref = lemma_refs[0]
                full_lemma = cmap.span_attributes[lemma_ref].get("vollform")

                if full_lemma is None:
                    continue

                homograph_index = self._extract_homograph_index(cmap, lemma_ref)
                cmap.set_text(lemma_ref, full_lemma + homograph_index + ", ")

                if homograph_index:
                    start = cmap.get_span_range(lemma_ref)[0] + len(full_lemma)
                    cmap.add_span("hoch", start, start + len(homograph_index))

                # insert "Bed. " text
                cmap = cmap.insert(
                    cmap.get_span_range(lemma_ref)[1], "Bed. ", reference
                )

        return cmap

    @staticmethod
    def _extract_homograph_index(cmap: CharacterMap, lemma_ref: str) -> str:
        superscripts = cmap.get_subspans(lemma_ref, tag="hoch")
        if len(superscripts) == 0:
            return ""

        start, end = cmap.get_span_range(superscripts[0])
        return cmap.text[start:end].strip()

    @register("lemma-form")
    def serialize_mention(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("hoch")
    def serialize_superscript(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["superscript"])

    @register("beleg-text")
    def serialize_example(self, span: SpanView) -> TextAnnotationSpan:
        return TextAnnotationSpan(**textspan(span), labels=["italic"])

    @register("verweis")
    def serialize_reference(
        self, span: SpanView
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
        self, span: SpanView
    ) -> Union[CrossRefAnnotationSpan, LinkAnnotationSpan]:
        """Kompositum-nodes share the structure of verweis-nodes"""
        return self.serialize_reference(span)


class BdoLiteratureTransformer(StandoffTransformer):
    def set_bibliography_details(self, submap: CharacterMap) -> None:
        self._bibliography = submap

    def get_bibliography_details(self) -> CharacterMap | None:
        return getattr(self, "_bibliography", None)

    @preprocess(order=1)
    def insert_literature_prefixes(self, cmap: CharacterMap) -> CharacterMap:
        for span_id in cmap.spans("literatur-quelle"):
            start, _ = cmap.get_span_range(span_id)
            attributes = cmap.span_attributes[span_id]

            cmap = cmap.insert(start, attributes.get("quelle-art", "") + " ")

        return cmap

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

        return cmap

    @register("literatur-quelle")
    def serialize_bibref(self, span: SpanView) -> Union[BibRefAnnotationSpan, None]:
        details = self.get_bibliography_details()

        if details is None:
            return None

        details_transformer = BdoBaseTransformer.from_cmap(details)

        return BibRefAnnotationSpan(
            **basedata(span, "bibref"),
            bibId=span.get("literatur", ""),
            fullReference=AnnotatedTextData(**details_transformer.serialize()),
        )


class BdoMixedContentTransformer(BdoBaseTransformer, BdoLiteratureTransformer):
    pass
