from app.transformers.bdo.bdo_transformer import BdoXmlTransformer


def test_parse_simple_bdo(bdo_simple_xml_path, bdo_transformer, bdo_simple_json):
    result = bdo_transformer.transform(bdo_simple_xml_path)
    assert result == bdo_simple_json
