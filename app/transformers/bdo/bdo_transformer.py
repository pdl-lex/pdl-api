import csv
from pathlib import Path

from pydash import omit, unique_id

from app.transformers.base_xml_transformer import (
    BaseXmlTransformer,
    extract_text,
    xpath,
)
from app.transformers.bdo.bdo_mixed_content import BdoMixedContentTransformer

pos_map_path = Path(__file__).parent / "pos_mapping.csv"

with open(pos_map_path, newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    POS_MAPPING = {row["bdo_tag"]: row["normalized"] for row in reader}


def flatten_senses(senses: list):
    flat_senses = []

    for sense in senses:
        flat_senses.append(omit(sense, "sense"))
        flat_senses.extend(
            [] if sense is None else flatten_senses(sense.get("sense", []))
        )

    return flat_senses


def extract_examples(sense):
    examples = []

    for example in sense.findall("beleg-position/beleg-angabe"):
        text = getattr(example.find("beleg-text"), "text", None)
        if text is not None:
            examples.append(
                {
                    "type": "example",
                    "quote": text,
                }
            )

    return examples


def is_sense(element):
    return element is not None and element.find("bedeutung") is not None


def transform_sense(node):
    sense = node.find("bedeutung")
    text = extract_text(sense)

    number = node.attrib.get("nr")
    id_ = node.attrib.get("id", unique_id("sense_"))

    return {
        "def": text,
        "sourceId": id_,
        "n": number,
        "sense": [
            transform_sense(subsense)
            for subsense in node.findall("bedeutung-position")
            if is_sense(subsense)
        ],
        "cit": extract_examples(node),
    }


class BdoXmlTransformer(BaseXmlTransformer):
    @xpath(".//lemma", default="")
    def headword(self, lemma_node):
        return {
            "lemma": lemma_node.text,
            "index": getattr(lemma_node.find("hoch"), "text", None),
        }

    @xpath(".//lemma-position/lemma-variante/@vollform", multiple=True, default="")
    def variants(self, items):
        return items

    @xpath(".//artikel/@wb")
    def source(self, source):
        return source

    @xpath(".//artikel/@id", alias="sourceId")
    def source_id(self, id_):
        return id_

    @xpath(".//artikel/bedeutung-position", default=[], multiple=True)
    def sense(self, senses):
        return [transform_sense(sense) for sense in senses if is_sense(sense)]

    @xpath(".//lemma-position/grammatik/@wortart")
    def pos(self, value):
        return value

    @xpath(".//lemma-position/grammatik/@genus")
    def gender(self, value):
        return value

    @xpath(".//lemma-position/grammatik/@numerus")
    def number(self, value):
        return value

    @xpath(".//etymologie-position")
    def etym(self, node):
        if node is None:
            return None

        transformer = BdoMixedContentTransformer.load_xml(node)

        return transformer.serialize()

    def postprocess(self, data, _element):
        data["xml:lang"] = "DE"
        data["flatSenses"] = flatten_senses(data.get("sense", []))
        data["nPos"] = POS_MAPPING.get(data.get("pos"))

        return data
