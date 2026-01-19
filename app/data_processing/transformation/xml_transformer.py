from functools import wraps
from typing import Any, Callable, Optional

import lxml.etree as ET  # noqa: N812


class BaseXmlTransformer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()

    def transform(self, element: Optional[ET._Element] = None) -> dict:
        """Extract all fields marked with @xpath decorator."""
        result = {}

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_is_field"):
                key = (
                    attr._alias
                    if getattr(attr, "_alias", None) is not None
                    else attr_name
                )
                result[key] = attr(self.root)

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
                value = results[0] if results else default
                return func(self, value)

        wrapper._xpath = path
        wrapper._alias = alias
        wrapper._is_field = True

        return wrapper

    return decorator
