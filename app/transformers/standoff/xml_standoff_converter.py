import re
from copy import deepcopy


def normalize_whitespace(element, inplace=False):
    if not inplace:
        element = deepcopy(element)

    if element.text:
        element.text = re.sub(r"\s+", " ", element.text)
    if element.tail:
        element.tail = re.sub(r"\s+", " ", element.tail)

    for child in element:
        normalize_whitespace(child, inplace=True)

    return element


def xml_to_standoff(
    node, offset=0, depth=0, spans=None, basetext=None, normalize_ws=True
):
    if normalize_ws:
        node = normalize_whitespace(node)

    if spans is None:
        spans = []

    full_text = "".join(node.itertext())
    basetext = full_text if basetext is None else basetext
    end = offset + len(full_text)

    markable = (offset, end, depth, node.tag, node.attrib, basetext[offset:end])
    spans.append(markable)

    offset += len(node.text or "")

    for subnode in node:
        if not isinstance(subnode.tag, str):
            continue
        xml_to_standoff(
            subnode, offset, depth + 1, spans, basetext, normalize_ws=normalize_ws
        )
        offset += len("".join(subnode.itertext())) + len(subnode.tail or "")

    return spans
