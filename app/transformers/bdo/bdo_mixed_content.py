import pandas as pd

from app.models.annotated_text import AnnotatedText
from app.transformers.standoff import StandoffTransformer


class DetailsTransformer(StandoffTransformer):
    text_tags = {"hoch": ["sup"]}

    def serialize(self):
        tag_id = self.aframe.get_first("details").name
        aframe = self.aframe.get_subspans(tag_id)
        aframe = aframe.normalize_offsets()

        basetext = self.aframe.get_first("titel").text

        return {"text": basetext, "annotations": self.serialize_spans(only=["hoch"])}


class BdoMixedContentTransformer(StandoffTransformer):
    tag_names = {
        "verweis": "crossref",
        "literatur-quelle": "bibref",
    }
    attr_names = {
        "quelle-art": "prefix",
        "verweis-typ": "variant",
        "literatur": "bibId",
        "ziel": "target",
    }

    def process_crossref(self):
        self.aframe = self.aframe

    def _cleanup_bibref(self):
        self.aframe = self.aframe.remove_all_spans("details", remove_text=True)
        self.aframe = self.aframe.drop("prefix", axis=1)

    def process_bibref(self):
        full_references = pd.Series()

        for span in self.aframe.iter_spans("bibref"):
            details_transformer = DetailsTransformer(
                self.aframe.get_subspans(span.name)
            )
            full_references.loc[span.name] = details_transformer.serialize()

            if not pd.isna(prefix := span["prefix"]):
                self.aframe = self.aframe.insert_text(span.start, f"{prefix} ")

        self.aframe = self.aframe.add_attribute("fullReference", full_references)
        self._cleanup_bibref()

    def transform(self) -> AnnotatedText:
        self.process_bibref()
        serialized = {
            "text": self.basetext,
            "annotations": self.serialize_spans(
                only=["crossref", "bibref"], exclude_attributes=["ziel-typ"]
            ),
        }
        import json

        print(json.dumps(serialized, indent=2, ensure_ascii=False))
        AnnotatedText.model_validate(serialized)
