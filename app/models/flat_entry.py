from datetime import date
from enum import Enum
from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel

from app.models.annotated_text import AnnotatedTextData
from app.models.rich_text import RichTextField


class Resource(Enum):
    BDO = "bdo"
    BWB = "bwb"
    DIBS = "dibs"
    WBF = "wbf"
    DWDS = "dwds"


BDO_RESOURCES = [Resource.BWB, Resource.DIBS, Resource.WBF]


class Form(SQLModel):
    orth: Optional[str] = ""
    n: Optional[str] = None
    type_: str = Field(alias="type")
    form: Optional[list["Form"]] = []


class Citation(AnnotatedTextData):
    type_: str = Field(alias="type")


class Sense(SQLModel):
    n: Optional[str] = None
    def_: Optional[str] = Field(alias="def", default="")
    sense: list["Sense"] = []
    cit: Optional[list[Citation]] = []
    usg: Optional[list[dict]] = []
    source_id: Optional[str] = Field(alias="sourceId", default=None)
    entry: Optional[list[dict]] = []


class EtymologySegment(SQLModel):
    type_: str = Field(alias="type")
    content: RichTextField


class Etymology(SQLModel):
    content: Optional[list[EtymologySegment]] = []
    ref: Optional[list[dict]] = []
    note: Optional[list[dict]] = []


class GrammarFeature(SQLModel):
    text: str
    type_: str = Field(alias="type")


class GrammarGroup(SQLModel):
    gram: list[GrammarFeature]


class BiblItem(SQLModel):
    note: Optional[list[dict]] = []
    title: dict
    bibl_scope: dict = Field(alias="biblScope")


class ListBibl(SQLModel):
    bibl: Optional[list] = []
    head: str
    type_: str = Field(alias="type")


class MediaFile(SQLModel):
    url: str
    author: str
    title: str
    license: str


class CrossReference(SQLModel):
    ref: Optional[list] = []
    type_: Optional[str] = Field(alias="type")
    subtype: Optional[str] = None


class GrammaticalFeatures:
    gender: Optional[str] = None
    pos: Optional[str] = None
    number: Optional[str] = None
    normalized_pos: Optional[str] = Field(alias="nPos", default=None)
    normalized_gender: Optional[str] = Field(alias="nGender", default=None)


class Entry(SQLModel, GrammaticalFeatures):
    headword: str
    headword_subscript: int = Field(alias="headwordSubscript")
    lex_id: str = Field(alias="lexId")
    retrieved_at: Optional[date] | None = Field(alias="retrievedAt", default=None)
    uploaded_at: Optional[date] | None = Field(alias="uploadedAt", default=None)
    source_id: Optional[str] = Field(alias="sourceId", default=None)
    source: Resource
    original_source: Optional[str] = Field(alias="originalSource", default=None)
    source_url: Optional[str] = Field(alias="sourceUrl", default=None)
    index_letter: str = Field(
        alias="indexLetter", min_length=1, max_length=1, default="#"
    )
    variants: list[str]
    flat_senses: Optional[list[Sense]] = Field(alias="flatSenses", default=[])
    etym: Optional[AnnotatedTextData] = None
    sense: Optional[list[Sense]] = []
    xml_lang: str = Field(alias="xml:lang")
    list_bibl: Optional[ListBibl] = Field(alias="listBibl", default=None)
    xr: Optional[list[CrossReference]] = []
    family: list[str] | None = None
    derivations: list[AnnotatedTextData] | None = []
    compounds: list[AnnotatedTextData] | None = []
    additional_info_type_available: Optional[list[str]] = Field(
        alias="additionalInfoTypeAvailable", default=[]
    )
    cit: Optional[list[Citation]] = []
    media_files: Optional[list[MediaFile]] = Field(alias="mediaFiles", default=[])


class EntryList(SQLModel):
    items: list[Entry]
    total: int
    page: int
    items_per_page: int = Field(alias="itemsPerPage")


class KeywordListItem(SQLModel):
    lemma: str


class KeywordList(SQLModel):
    items: list[KeywordListItem]
    total: int
    page: int
    items_per_page: int = Field(alias="itemsPerPage")
