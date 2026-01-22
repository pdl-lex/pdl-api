from typing import Annotated, Union

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
    bib_id: str = Field(alias="bibId")


class LinkAnnotationSpan(BaseAnnotationSpan):
    type: Literal["link"]
    target: str


class CrossRefAnnotationSpan(LinkAnnotationSpan):
    type: Literal["crossref"]
    variant: str


AnnotationSpan = Annotated[
    Union[
        TextAnnotationSpan,
        BibRefAnnotationSpan,
        CrossRefAnnotationSpan,
        LinkAnnotationSpan,
    ],
    Field(discriminator="type"),
]
