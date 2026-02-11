from enum import Enum
from typing import Optional, Union

from pydantic import Field

from app.models.annotated_text import AnnotatedText
from app.models.annotated_text_display import AnnotatedTextDisplay
from app.models.base import BaseModel
from app.models.rich_text import RichTextField


class Resource(Enum):
    BWB = "bwb"
    DIBS = "dibs"
    WBF = "wbf"


class Form(BaseModel):
    orth: Optional[str] = ""
    n: Optional[str] = None
    type_: str = Field(alias="type")
    form: Optional[list["Form"]] = []


class Citation(BaseModel):
    bibl: Optional[list[dict]] = []
    type_: str = Field(alias="type")
    quote: Optional[str] = None
    source_id: Optional[str] = Field(alias="sourceId", default=None)
    note: Optional[list[dict]] = []


class Sense(BaseModel):
    n: Optional[str] = None
    def_: Optional[str] = Field(alias="def", default="")
    sense: list["Sense"] = []
    cit: Optional[list[Citation]] = []
    usg: Optional[list[dict]] = []
    source_id: Optional[str] = Field(alias="sourceId", default=None)
    entry: Optional[list[dict]] = []


class EtymologySegment(BaseModel):
    type_: str = Field(alias="type")
    content: RichTextField


class Etymology(BaseModel):
    content: Optional[list[EtymologySegment]] = []
    ref: Optional[list[dict]] = []
    note: Optional[list[dict]] = []


class GrammarFeature(BaseModel):
    text: str
    type_: str = Field(alias="type")


class GrammarGroup(BaseModel):
    gram: list[GrammarFeature]


class BiblItem(BaseModel):
    note: Optional[list[dict]] = []
    title: dict
    bibl_scope: dict = Field(alias="biblScope")


class ListBibl(BaseModel):
    bibl: Optional[list] = []
    head: str
    type_: str = Field(alias="type")


class CrossReference(BaseModel):
    ref: Optional[list] = []
    type_: Optional[str] = Field(alias="type")
    subtype: Optional[str] = None


class AbstractBaseEntry(BaseModel):
    etym: Optional[list[Etymology] | list[str]] = []
    sense: Optional[list[Sense]] = []
    source_id: Optional[str] = Field(alias="sourceId", default=None)
    lex_id: str = Field(alias="lexId")
    xml_lang: str = Field(alias="xml:lang")
    list_bibl: Optional[ListBibl] = Field(alias="listBibl", default=None)
    xr: Optional[list[CrossReference]] = []
    family: list[str] | None = None
    derivations: list[AnnotatedTextDisplay | AnnotatedText] | None = []
    compounds: list[AnnotatedTextDisplay | AnnotatedText] | None = []


class GrammaticalFeatures:
    gender: Optional[str] = None
    pos: Optional[str] = None
    number: Optional[str] = None
    normalized_pos: Optional[str] = Field(alias="nPos", default=None)


class Entry(AbstractBaseEntry):
    form: list[Form]
    gram_grp: Optional[list[GrammarGroup]] = Field(alias="gramGrp", default=None)


class Headword(BaseModel):
    lemma: str
    index: Optional[int] = None


class DisplayEntry(AbstractBaseEntry, GrammaticalFeatures):
    headword: Headword
    source: Resource
    variants: list[str]
    flat_senses: Optional[list[Sense]] = Field(alias="flatSenses", default=[])
    etym: Optional[Union[AnnotatedTextDisplay, AnnotatedText]] = None


class DisplayEntryList(BaseModel):
    items: list[DisplayEntry]
    total: int
    page: int
    items_per_page: int = Field(alias="itemsPerPage")
