from app.transformers.base_xml_transformer import (
    BaseXmlTransformer,
    extract_text,
    xpath,
)


class DwdsXmlTransformer(BaseXmlTransformer):
    @xpath(".//Schreibung")
    def headword(self, node):
        if node is None:
            return {"lemma": "", "index": None}

        return {"lemma": extract_text(node), "index": node.attrib.get("hidx")}

    @xpath(".")
    def source(self, _):
        return "dwds"

    @xpath(".//Artikel/@xml:id", alias="sourceId")
    def source_id(self, id_):
        return id_
