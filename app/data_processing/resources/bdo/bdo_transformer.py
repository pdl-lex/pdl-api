import json
from pathlib import Path

from pydash import omit, unique_id

from app.data_processing.resources.bdo.bdo_standoff import process_etymology
from app.data_processing.transformation.base_xml_transformer import (
    BaseXmlTransformer,
    xpath,
)
from app.models.entry import DisplayEntry

pos_map_path = Path(__file__).parent / "pos_mapping.json"

with open(pos_map_path) as f:
    POS_MAP = json.load(f)


def flatten_senses(senses: list):
    flat_senses = []

    for sense in senses:
        flat_senses.append(omit(sense, "sense"))
        flat_senses.extend(flatten_senses(sense.get("sense", [])))

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


def transform_sense(node):
    text = node.find("bedeutung").text
    number = node.attrib.get("nr")
    id_ = node.attrib.get("id", unique_id("sense_"))

    return {
        "def": text,
        "xml:id": id_,
        "n": number,
        "sense": [
            transform_sense(subsense) for subsense in node.findall("bedeutung-position")
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

    @xpath(".//artikel/@id", alias="xml:id")
    def xml_id(self, id_):
        return id_

    @xpath(".//artikel/bedeutung-position", default="", multiple=True)
    def sense(self, senses):
        return [transform_sense(sense) for sense in senses]

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
    def etym(self, value):
        standoff = process_etymology(value)

        return standoff

    def postprocess(self, data, _element):
        data["xml:lang"] = "DE"
        data["flatSenses"] = flatten_senses(data.get("sense", []))
        data["nPos"] = POS_MAP[data["pos"]] if "pos" in data else None

        return data
