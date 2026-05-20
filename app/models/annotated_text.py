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
    bibliography_url: Optional[str] = Field(alias="bibliographyUrl", default=None)


class LinkAnnotationSpan(BaseAnnotationSpan):
    type: Literal["link"]
    target: str


class CrossRefAnnotationSpan(LinkAnnotationSpan):
    type: Literal["crossref"]
    variant: Optional[str] = None
    missing: Optional[bool] = False


class XmlAttributeSpan(BaseAnnotationSpan):
    type: Literal["xmlattribute"]
    from_tag: str = Field(alias="fromTag")
    from_attribute: str = Field(alias="fromAttribute")
    value: str


AnnotationSpan = Annotated[
    Union[
        TextAnnotationSpan,
        BibRefAnnotationSpan,
        CrossRefAnnotationSpan,
        LinkAnnotationSpan,
        XmlAttributeSpan,
    ],
    Field(discriminator="type"),
]


class AnnotatedTextData(BaseModel):
    text: str
    annotations: list[AnnotationSpan]
