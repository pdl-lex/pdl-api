from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from app.models.base import BaseModel


class BaseDisplay(BaseModel):
    text: str


class BaseContainerDisplay(BaseDisplay):
    content: list["SpanDisplay"]


class TextDisplay(BaseDisplay):
    type: Literal["text"] = "text"
    labels: Optional[list[str]] = None


class LinkDisplay(BaseContainerDisplay):
    type: Literal["link"] = "link"
    target: str


class CrossRefDisplay(LinkDisplay):
    type: Literal["crossref"] = "crossref"
    variant: Optional[str] = None


class BibRefDisplay(BaseContainerDisplay):
    type: Literal["bibref"] = "bibref"
    bib_id: str = Field(alias="bibId", default="")
    full_reference: "AnnotatedTextDisplay" = Field(alias="fullReference")


SpanDisplay = Annotated[
    Union[
        TextDisplay,
        LinkDisplay,
        CrossRefDisplay,
        BibRefDisplay,
    ],
    Field(discriminator="type"),
]


class AnnotatedTextDisplay(BaseModel):
    text: str
    content: list[SpanDisplay]
