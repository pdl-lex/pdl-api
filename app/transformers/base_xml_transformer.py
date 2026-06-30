import re
from collections import Counter
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

import lxml.etree as ET  # noqa: N812
from pydash import omit
from unidecode import unidecode


class TransformationError(ValueError):
    pass


def extract_text(node) -> str | None:
    if node is None:
        return None

    raw_text = "".join(node.itertext())
    return " ".join(re.split(r"\s+", raw_text))


def flatten_senses(senses: list):
    flat_senses = []

    for sense in senses:
        flat_senses.append(omit(sense, "sense"))
        flat_senses.extend(
            [] if sense is None else flatten_senses(sense.get("sense", []))
        )

    return flat_senses


class BaseXmlTransformer:
    def _prepare_tree(self, root):
        """Hook for subclasses to modify the parsed tree before extraction.

        Override this method to strip namespaces, normalize elements,
        or perform any other tree-level preprocessing.

        Args:
            root: The root element of the parsed XML tree

        Returns:
            The (possibly modified) root element
        """
        return root

    def transform(self, filepath: Path, element: Optional[ET._Element] = None) -> dict:
        """Extract all fields marked with @xpath decorator."""
        result = {}
        self.tree = ET.parse(filepath)
        self.root = self._prepare_tree(self.tree.getroot())

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
                        f"Error transforming {attr_name} in {filepath}"
                    ) from err

        result = self.postprocess(result, element)

        return result

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

        wrapper._xpath = path  # pyright: ignore[reportAttributeAccessIssue]
        wrapper._alias = alias  # pyright: ignore[reportAttributeAccessIssue]
        wrapper._is_field = True  # pyright: ignore[reportAttributeAccessIssue]

        return wrapper

    return decorator
