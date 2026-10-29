# See Readme.md in app/transformers/awb/ for details on the AWB data and transformation approach.

import csv
from pathlib import Path

from app.transformers.base_xml_transformer import (
    BaseXmlTransformer,
    extract_text,
    flatten_senses,
    xpath,
)

ADDITIONAL_INFO_FIELDS = {
    "Etymologie": './/sense[@ana="verweisblock"]',
    "Formen": './/sense[@ana="formblock"]',
    "Kommentar": './/sense[@ana="kommentarblock"]',
}

GENDER_ABBREVIATIONS = {"m.", "f.", "n."}

gender_map_path = Path(__file__).parent / "gender_mapping.csv"
with open(gender_map_path, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    GENDER_MAPPING = {row["awb_tag"]: row["normalized"] for row in reader}

pos_map_path = Path(__file__).parent / "pos_mapping.csv"
with open(pos_map_path, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    POS_MAPPING = {row["awb_tag"]: row["normalized"] for row in reader}


# --- Sense extraction chain (module-level, matches BDO pattern) ---


def _text_without_orig(node):
    """Return the text of a node, skipping the <orig> part of <choice> so only <reg> remains."""
    return "".join(node.xpath(".//text()[not(ancestor::orig)]"))


def split_sense_text(node):
    """Split a meaning block into the leading definition and the remaining citation text.

    The definition is the run of <hi>/<lb> elements at the start of the block, up to
    the first plain text. The bold sense number and nested sub-senses are skipped.
    """
    definition = []
    rest = [node.text or ""]
    in_definition = not (node.text or "").strip()

    for child in node:
        if child.tag == "sense":
            continue

        is_number = child.tag == "hi" and child.get("rend") == "bold" and not definition
        if in_definition and child.tag in ("hi", "lb"):
            target = definition
        else:
            in_definition = False
            target = rest
        if not is_number:
            target.append(_text_without_orig(child))

        tail = child.tail or ""
        if tail.strip():
            in_definition = False
        (definition if in_definition else rest).append(tail)

    definition_text = " ".join("".join(definition).split()).rstrip(":").strip()
    rest_text = " ".join("".join(rest).split())
    return definition_text, rest_text


def transform_sense(node):
    """Transform a meaning block into a sense dict with definition, citation text, and recursively nested sub-senses."""
    definition, citation = split_sense_text(node)
    return {
        "def": {"text": definition, "annotations": []},
        "sourceId": node.get("value"),
        "n": node.get("n"),
        "sense": [
            transform_sense(subsense)
            for subsense in node.findall("sense[@ana='bedeutungsblock']")
        ],
        "cit": (
            [{"text": citation, "type": "attested", "annotations": []}]
            if citation
            else []
        ),
    }


# --- Transformer class ---


class AwbXmlTransformer(BaseXmlTransformer):
    # --- @xpath field extractors ---

    @xpath("form[@type='headword']/form[@type='lemma']", default=None)
    def headword(self, node):
        if node is None:
            return {"lemma": "", "index": 0}
        return {
            "lemma": (extract_text(node) or "").strip(),
            "index": 0,  # TODO: Determine homograph index if available in the XML
        }

    @xpath("form[@type='headword']/form[@type='variant']", default=[], multiple=True)
    def variants(self, nodes):
        return [(extract_text(node) or "").strip() for node in nodes]

    @xpath("@xml:id", alias="sourceId")
    def source_id(self, id_):
        return id_

    @xpath("sense[@ana='bedeutungsblock']", default=[], multiple=True)
    def sense(self, senses):
        return [transform_sense(sense) for sense in senses if sense is not None]

    @xpath("form[@type='headword']/form[@type='lemma']/@n")
    def pos(self, value):
        return value

    @xpath("form[@type='headword']/form[@type='lemma']/@n")
    def gender(self, value):
        if value is None:
            return None
        return next(
            (part for part in value.split() if part in GENDER_ABBREVIATIONS), None
        )

    # --- Static utilities ---

    @staticmethod
    def _build_source_url(source_id: str | None) -> str | None:
        """Build the AWB online dictionary URL from the article ID."""
        if not source_id:
            return None
        return f"https://awb.saw-leipzig.de/AWB?lemid={source_id}"

    @staticmethod
    def _has_text(node) -> bool:
        text = extract_text(node)
        return text is not None and text.strip() != ""

    @staticmethod
    def _any_has_text(nodes) -> bool:
        return any(AwbXmlTransformer._has_text(n) for n in nodes)

    # --- Private extraction methods (use self.root) ---

    def _detect_additional_info_types(self) -> list[str]:
        """Detect which additional information categories (e.g. etymology) are present in the article."""
        return [
            name
            for name, path in ADDITIONAL_INFO_FIELDS.items()
            if self._any_has_text(self.root.xpath(path))
        ]

    # --- Postprocess ---

    def postprocess(self, data, _element):
        """Enrich the transformed entry with flat senses, gender mapping, and additional metadata."""
        data["xml:lang"] = "DE"
        data["source"] = "awb"
        flat_senses = flatten_senses(data.get("sense", []))
        data["flatSenses"] = flat_senses
        data["sourceUrl"] = self._build_source_url(data.get("sourceId"))
        data["nGender"] = GENDER_MAPPING.get(data.get("gender"))
        data["nPos"] = POS_MAPPING.get(data.get("pos"))
        data["additionalInfoTypeAvailable"] = self._detect_additional_info_types()

        return data
