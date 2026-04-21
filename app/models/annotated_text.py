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
    full_reference: Optional["AnnotatedTextData"] = Field(
        alias="fullReference", default=None
    )
    target: Optional[str] = None


class LinkAnnotationSpan(BaseAnnotationSpan):
    type: Literal["link"]
    target: str


class CrossRefAnnotationSpan(LinkAnnotationSpan):
    type: Literal["crossref"]
    variant: Optional[str] = None
    missing: Optional[bool] = False


AnnotationSpan = Annotated[
    Union[
        TextAnnotationSpan,
        BibRefAnnotationSpan,
        CrossRefAnnotationSpan,
        LinkAnnotationSpan,
    ],
    Field(discriminator="type"),
]


class AnnotatedTextData(BaseModel):
    text: str
    annotations: list[AnnotationSpan]
