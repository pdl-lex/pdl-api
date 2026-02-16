import re
from collections import Counter
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

import lxml.etree as ET  # noqa: N812
from unidecode import unidecode


class TransformationError(ValueError):
    pass


def extract_text(node) -> str | None:
    if node is None:
        return None

    raw_text = "".join(node.itertext())
    return " ".join(re.split(r"\s+", raw_text))


class BaseXmlTransformer:
    def __init__(self):
        self._lex_ids = Counter()

    def _add_lex_id(self, entry: dict) -> dict:
        pos_abbreviations = {"Substantiv": "n", "Verb": "v", "Adjektiv": "a"}
        lemma_index = entry["headword"]["index"]
        lemma = unidecode(entry["headword"]["lemma"].lower())

        lex_id = "__".join(
            [
                "lex",
                entry["source"],
                f"{lemma}{'' if lemma_index == 0 else lemma_index}",
                pos_abbreviations.get(entry["nPos"], "o"),  # o = other
            ]
        )
        self._lex_ids[lex_id] += 1

        if (count := self._lex_ids[lex_id]) > 1:
            lex_id += f"__{count}"

        return {**entry, "lexId": lex_id}

    def transform(self, filepath: Path, element: Optional[ET._Element] = None) -> dict:
        """Extract all fields marked with @xpath decorator."""
        result = {}
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_is_field"):
                key = (
                    attr._alias
                    if getattr(attr, "_alias", None) is not None
                    else attr_name
                )
                try:
                    result[key] = attr(self.root)
                except AttributeError as err:
                    raise TransformationError(
                        f"Error transforming {attr_name} in {self.filepath}"
                    ) from err

        result = self.postprocess(result, element)

        return self._add_lex_id(result)

    def postprocess(self, data: dict, element: ET._Element) -> dict:
        """Hook for modifying transformed data.

        Override this method in subclasses to add computed fields,
        restructure data, or perform validation.

        Args:
            data: Dictionary of extracted fields
            element: The XML element that was transformed

        Returns:
            Modified data dictionary
        """
        return data


def xpath(
    path: str,
    multiple: bool = False,
    alias: Optional[str] = None,
    default: Any = None,
):
    """Decorator to extract data via XPath and pass to method.

    Args:
        path: XPath expression to extract nodes
        multiple: If True, pass all results as a list
        alias: Alternative field name
        default: Default value if no results found
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, element) -> Any:
            results = element.xpath(path)

            if multiple:
                return func(self, results)
            else:
                value = results[0] if len(results) > 0 else default
                return func(self, value)

        wrapper._xpath = path
        wrapper._alias = alias
        wrapper._is_field = True

        return wrapper

    return decorator
