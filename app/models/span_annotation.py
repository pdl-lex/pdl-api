from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from app.models.base import BaseModel


class BaseSpanDisplay(BaseModel):
    text: str


class BaseSpanContainerDisplay(BaseSpanDisplay):
    content: list["SpanDisplay"]


class TextSpanDisplay(BaseSpanDisplay):
    type: Literal["text"] = "text"
    labels: Optional[list[str]] = None


class LinkSpanDisplay(BaseSpanContainerDisplay):
    type: Literal["link"] = "link"
    target: str


class CrossRefSpanDisplay(LinkSpanDisplay):
    type: Literal["crossref"] = "crossref"
    variant: Optional[str] = None


class BibRefSpanDisplay(BaseSpanContainerDisplay):
    type: Literal["bibref"] = "bibref"
    bib_id: str = Field(alias="bibId", default="")
    full_reference: "AnnotatedTextDisplay" = Field(alias="fullReference")


SpanDisplay = Annotated[
    Union[
        TextSpanDisplay,
        LinkSpanDisplay,
        CrossRefSpanDisplay,
        BibRefSpanDisplay,
    ],
    Field(discriminator="type"),
]


class AnnotatedTextDisplay(BaseModel):
    text: str
    spans: list[SpanDisplay]
