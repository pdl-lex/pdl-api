from typing import Annotated, Literal, Union

from pydantic import Field

from app.models.base import BaseModel


class RichTextSegment(BaseModel):
    type: str


class PlainTextSegment(RichTextSegment):
    type: Literal["text"] = "text"
    body: str


class EmphasisSegment(RichTextSegment):
    type: Literal["emph"] = "emph"
    body: str


class SuperscriptSegment(RichTextSegment):
    type: Literal["sup"] = "sup"
    body: str


class LinkSegment(RichTextSegment):
    type: Literal["link"] = "link"
    url: str
    text: str


class CrossReferenceSegment(RichTextSegment):
    type: Literal["crossref"] = "crossref"
    target_id: str = Field(alias="targetId")
    text: str


class BibliographicalReferenceSegment(RichTextSegment):
    type: Literal["bibref"] = "bibref"
    details: "RichTextField"
    text: str


AnyRichTextSegment = Annotated[
    Union[
        PlainTextSegment,
        EmphasisSegment,
        SuperscriptSegment,
        LinkSegment,
        CrossReferenceSegment,
        BibliographicalReferenceSegment,
    ],
    Field(discriminator="type"),
]

RichTextField = list[AnyRichTextSegment]
