from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from app.models.base import BaseModel


class BaseAnnotationSpan(BaseModel):
    start: int
    end: int
    text: str


class TextSpan(BaseAnnotationSpan):
    type: Literal["text"] = "text"
    labels: Optional[list[str]] = None


class LinkSpan(BaseAnnotationSpan):
    type: Literal["link"] = "link"
    target: str


class CrossRefSpan(BaseAnnotationSpan):
    type: Literal["crossref"] = "crossref"
    target: str
    variant: Optional[str] = None


class BibRefSpan(BaseAnnotationSpan):
    type: Literal["bibref"] = "bibref"
    bib_id: str = Field(alias="bibId", default="")
    full_reference: str = Field(alias="fullReference", default="")


AnnotationSpan = Annotated[
    Union[TextSpan, LinkSpan, CrossRefSpan, BibRefSpan], Field(discriminator="type")
]


class AnnotatedText(BaseModel):
    text: str
    spans: list[AnnotationSpan]
