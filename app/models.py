from enum import Enum
from typing import Optional

from pydantic import BaseModel as DefaultModel
from pydantic import ConfigDict, Field


class BaseModel(DefaultModel):
    model_config = ConfigDict(extra="forbid")


class Dictionary(Enum):
    BWB = "bwb"
    WBF = "wbf"
    DIBS = "dibs"


class LemmaItem(BaseModel):
    source: Dictionary
    lemma: str
    pos: str


class LemmaResult(BaseModel):
    results: list[LemmaItem]


class Form(BaseModel):
    orth: str
    type_: str = Field(alias="type")


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bibl: list[dict]
    type_: str = Field(alias="type")
    quote: str
    xml_id: str = Field(alias="xmlId")


class Sense(BaseModel):
    n: str
    def_: str = Field(alias="def")
    sense: list["Sense"] = []
    cit: Optional[list[Citation]] = []
    usg: Optional[list[dict]] = []
    xml_id: str = Field(alias="xmlId")
    entry: Optional[list[dict]] = []


class EtymologySegment(BaseModel):
    type_: str = Field(alias="type")
    value: str


class Etymology(BaseModel):
    content: list[EtymologySegment]


class GrammarFeature(BaseModel):
    text: str
    type_: str = Field(alias="type")


class GrammarGroup(BaseModel):
    gram: GrammarFeature


class BiblItem(BaseModel):
    note: list[dict]
    title: dict
    bibl_scope: dict = Field(alias="biblScope")


class ListBibl(BaseModel):
    bibl: list
    head: str
    type_: str = Field(alias="type")


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    etym: Optional[Etymology] = None
    form: list[Form]
    sense: list[Sense]
    xml_id: str = Field(alias="xmlId")
    xml_lang: str = Field(alias="xmlLang")
    gram_grp: GrammarGroup = Field(alias="gramGrp")
    list_bibl: ListBibl = Field(alias="listBibl")
