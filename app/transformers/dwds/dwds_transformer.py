# See readme.md in app/transformers/dwds/ for details on the DWDS data and transformation approach.

import csv
from pathlib import Path
from urllib.parse import quote

from pydash import omit, unique_id

from app.transformers.base_xml_transformer import (
    BaseXmlTransformer,
    extract_text,
    xpath,
)
from app.transformers.dwds.dwds_mixed_content import DwdsMixedContentTransformer

ADDITIONAL_INFO_FIELDS = {
    "Aussprache": ".//IPA",
    "Etymologie": './/Etymologie | .//Verweis[@Typ="EtymWB"]',
    "Syntagmatik": ".//Lesart/Syntagmatik",
    "Diasystematik": ".//Lesart/Diasystematik",
    "Kollokationen": ".//Lesart/Kollokationen",
    "Illustration": ".//Lesart/Illustration",
    "Korpusbeispiele": ".//Rohdaten/Verwendungsbeispiele/Beleg/Belegtext",
    "Antonyme": './/Verweis[@Typ="Antonym"]',
    "Mehrwortausdrücke": './/Verweis[@Typ="MWA"]',
}

gender_map_path = Path(__file__).parent / "gender_mapping.csv"
with open(gender_map_path, newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    GENDER_MAPPING = {row["dwds_tag"]: row["normalized"] for row in reader}


# --- Sense extraction chain (module-level, matches BDO pattern) ---


def flatten_senses(senses: list):
    """Recursively flatten a nested sense tree into a flat list, preserving all senses including parents."""
    flat_senses = []

    for sense in senses:
        flat_senses.append(omit(sense, "sense"))
        flat_senses.extend(
            [] if sense is None else flatten_senses(sense.get("sense", []))
        )

    return flat_senses


def parse_fundstelle(beleg_node, text_length: int = 0):
    """Parse <Fundstelle> into a BibRefAnnotationSpan dict to be added to annotations."""
    fundstelle = beleg_node.find("Fundstelle")
    if fundstelle is None:
        return None

    sigle = fundstelle.get("Sigle", "")
    fundort = fundstelle.get("Fundort", "")

    has_children = any(child.text for child in fundstelle if isinstance(child.tag, str))

    if has_children:
        full_reference = DwdsMixedContentTransformer.load_xml(fundstelle).serialize()
        # Strip leading/trailing whitespace from XML indentation and adjust offsets
        text = full_reference["text"]
        lstrip_len = len(text) - len(text.lstrip())
        full_reference["text"] = text.strip()
        full_reference["annotations"] = [
            {**ann, "start": ann["start"] - lstrip_len, "end": ann["end"] - lstrip_len}
            for ann in full_reference["annotations"]
            if ann["start"]
            != ann["end"]  # filter out zero-width spans (empty elements)
        ]
    else:
        full_reference = {"text": (fundstelle.text or "").strip(), "annotations": []}

    return {
        "type": "bibref",
        "start": text_length,
        "end": text_length,
        "text": "",
        "bibId": sigle or fundort or "",
        "fullReference": full_reference,
    }


def _serialize_beleg(node, type_: str):
    """Serialize a <Beleg> or <Kompetenzbeispiel> node into a citation dict with annotations and bibliographic reference."""
    data = DwdsMixedContentTransformer.load_xml(node.find("Belegtext")).serialize()
    fundstelle = parse_fundstelle(node, text_length=len(data["text"]))
    if fundstelle is not None:
        data["annotations"].append(fundstelle)
    return {**data, "type": type_}


def extract_constructed_examples(sense):
    """Extract constructed (editorial) usage examples from a sense node."""
    return [
        {
            **DwdsMixedContentTransformer.load_xml(node.find("Belegtext")).serialize(),
            "type": "constructed",
        }
        for node in sense.findall("Verwendungsbeispiele/Kompetenzbeispiel")
    ]


def extract_attested_examples(sense):
    """Extract attested (corpus-based) usage examples from a sense node."""
    return [
        _serialize_beleg(node, "attested")
        for node in sense.findall("Verwendungsbeispiele/Beleg")
    ]


def extract_examples(sense):
    """Extract all usage examples (constructed + attested) from a sense node."""
    return extract_constructed_examples(sense) + extract_attested_examples(sense)


def transform_sense(node):
    """Transform a <Lesart> node into a sense dict with definition, examples, and recursively nested sub-senses."""
    text = "" if (sense := node.find("Definition")) is None else extract_text(sense)

    number = node.attrib.get("n")
    id_ = node.attrib.get("xml:id", unique_id("sense_"))

    return {
        "def": text,
        "sourceId": id_,
        "n": number,
        "sense": [
            transform_sense(subsense)
            for subsense in node.findall("Lesart")
            if subsense is not None
        ],
        "cit": extract_examples(node),
    }


# --- Transformer class ---


class DwdsXmlTransformer(BaseXmlTransformer):
    # --- Tree preparation ---

    def _prepare_tree(self, root):
        """
        Remove namespaces and processing instructions from the XML tree to simplify XPath queries and clean up editor artifacts.
        """

        # As a { can only appear in a namespace declaration, we can safely split on it and take the second part as the tag name.
        # Thus works for all namespaces.
        for el in root.iter():
            if isinstance(el.tag, str) and "{" in el.tag:
                el.tag = el.tag.split("}", 1)[1]

        # removes all pi nodes from their parents
        # for DWDS, specifically removes the processing instructions that contain editor comments
        # Before removing, preserve any tail text by appending it to the previous sibling's tail
        # or the parent's text, so that e.g. <Schreibung><?oxy_comment_end?>du</Schreibung>
        # correctly retains "du" after the PI is removed.
        for pi in root.xpath("//processing-instruction()"):
            parent = pi.getparent()
            prev = pi.getprevious()
            if pi.tail:
                if prev is not None:
                    prev.tail = (prev.tail or "") + pi.tail
                else:
                    parent.text = (parent.text or "") + pi.tail
            parent.remove(pi)

        return root

    # --- @xpath field extractors ---

    @xpath(".//Schreibung", default=None)
    def headword(self, node):
        if node is None:
            return {"lemma": "", "index": 0}
        return {
            "lemma": node.text or "",
            "index": int(node.get("hidx", "0")),
        }

    # Specifies the data source the DWDS entry was taken from, e.g. "DWDS", "DWB", "DWDEtym", etc.
    @xpath(".//Artikel/@Quelle", alias="originalSource")
    def original_source(self, source):
        return source

    @xpath(".//Formangabe/@Quelle", default="DWDS")
    def source(self, source):
        return source.lower() if isinstance(source, str) else "dwds"

    @xpath(".//Artikel/@xml:id", alias="sourceId")
    def source_id(self, id_):
        return id_

    @xpath(".//Artikel/Lesart", default=[], multiple=True)
    def sense(self, senses):
        return [transform_sense(sense) for sense in senses if sense is not None]

    @xpath(".//Grammatik/Wortklasse")
    def pos(self, value):
        return value.text if value is not None else None

    @xpath(".//Grammatik/Genus")
    def gender(self, value):
        return value.text if value is not None else None

    # --- Static utilities ---

    @staticmethod
    def _build_source_url(headword: dict) -> str:
        """Build the full DWDS dictionary URL from lemma and homograph index."""
        lemma = quote(headword.get("lemma", ""), safe="")
        index = headword.get("index", 0)
        url = f"https://www.dwds.de/wb/{lemma}"
        if index > 0:
            url += f"#{index}"
        return url

    @staticmethod
    def _has_text(node) -> bool:
        text = extract_text(node)
        return text is not None and text.strip() != ""

    @staticmethod
    def _any_has_text(nodes) -> bool:
        return any(DwdsXmlTransformer._has_text(n) for n in nodes)

    # --- Private extraction methods (use self.root) ---

    def _detect_additional_info_types(self) -> list[str]:
        """Detect which additional information categories (e.g. etymology, pronunciation) are present in the article."""
        return [
            name
            for name, path in ADDITIONAL_INFO_FIELDS.items()
            if self._any_has_text(self.root.xpath(path))
        ]

    def _extract_media_files(self) -> list[dict]:
        """Extract illustration metadata (URL, author, title, license) from the article."""
        result = []
        for node in self.root.xpath(".//Illustration"):
            fundstelle = node.find("Fundstelle")
            if fundstelle is None:
                continue
            url = fundstelle.findtext("URL")
            author = fundstelle.findtext("Autor")
            title = fundstelle.findtext("Titel")
            license_ = node.get("Lizenz")
            if url and author and title and license_:
                result.append(
                    {
                        "url": url,
                        "author": author,
                        "title": title,
                        "license": license_,
                    }
                )
        return result

    def _extract_corpus_examples(self) -> list[dict]:
        """Extract corpus examples from the <Rohdaten> section at article level."""
        return [
            _serialize_beleg(node, "corpus_example")
            for node in self.root.findall(".//Rohdaten/Verwendungsbeispiele/Beleg")
        ]

    # --- Postprocess ---

    def postprocess(self, data, _element):
        """Enrich the transformed entry with flat senses, corpus examples, gender mapping, and additional metadata."""
        data["xml:lang"] = "DE"
        flat_senses = flatten_senses(data.get("sense", []))
        data["flatSenses"] = flat_senses
        data["cit"] = self._extract_corpus_examples()
        data["sourceUrl"] = self._build_source_url(data.get("headword", {}))
        data["nGender"] = GENDER_MAPPING.get(data.get("gender"))
        data["variants"] = []
        data["additionalInfoTypeAvailable"] = self._detect_additional_info_types()
        data["mediaFiles"] = self._extract_media_files()

        return data
