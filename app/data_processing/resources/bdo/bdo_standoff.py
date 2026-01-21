from copy import deepcopy

from app.data_processing.transformation.standoff.standoff_converter import (
    xml_to_standoff,
)


def inject_prefix(bib_node):
    if (prefix := bib_node.attrib.get("quelle-art")) is not None:
        if (previous_sibling := bib_node.getprevious()) is not None:
            previous_sibling.tail = (previous_sibling.tail or "") + prefix + " "
        else:
            parent = bib_node.getparent()
            parent.text = (parent.text or "") + f" {prefix} "


def process_etymology(node):
    node = deepcopy(node)
    details_list = []

    for bib_node in node.findall("literatur-quelle"):
        inject_prefix(bib_node)

        detail_node = bib_node.find("details")
        details_list.append(deepcopy(detail_node))
        bib_node.remove(detail_node)

    standoff = xml_to_standoff(node)

    basetext = standoff.pop(0)[-1]
    annotations = []

    for start, end, tag, attrib, text in standoff:
        if tag == "literatur-quelle":
            details = details_list.pop(0)
            annotations.append(
                {
                    "start": start,
                    "end": end,
                    "type": "bibref",
                    "text": text,
                    "bibId": attrib["literatur"],
                    "fullReference": details.find("titel").text,
                }
            )
        elif tag == "lemma-form":
            annotations.append(
                {
                    "start": start,
                    "end": end,
                    "type": "text",
                    "labels": ["mention"],
                    "text": text,
                }
            )
    return {
        "text": basetext,
        "spans": annotations,
    }
