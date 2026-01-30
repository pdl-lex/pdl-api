from typing import Annotated, Optional, Union

from pydantic import Field
from typing_extensions import Literal

from app.models.base import BaseModel


class BaseAnnotationSpan(BaseModel):
    start: int
    end: int
    text: str


class TextAnnotationSpan(BaseAnnotationSpan):
    type: Literal["text"]
    labels: list[str]


class BibRefAnnotationSpan(BaseAnnotationSpan):
    type: Literal["bibref"]
    bib_id: Optional[str] = Field(alias="bibId")
    full_reference: Optional["AnnotatedText"] = Field(
        alias="fullReference", default=None
    )


class LinkAnnotationSpan(BaseAnnotationSpan):
    type: Literal["link"]
    target: str


class CrossRefAnnotationSpan(LinkAnnotationSpan):
    type: Literal["crossref"]
    variant: Optional[str] = None


AnnotationSpan = Annotated[
    Union[
        TextAnnotationSpan,
        BibRefAnnotationSpan,
        CrossRefAnnotationSpan,
        LinkAnnotationSpan,
    ],
    Field(discriminator="type"),
]


class AnnotatedText(BaseModel):
    text: str
    annotations: list[AnnotationSpan]
