from typing import Optional

from pydantic import BaseModel as DefaultModel
from pydantic import ConfigDict, Field


class BaseModel(DefaultModel):
    model_config = ConfigDict(extra="forbid")


class Form(BaseModel):
    orth: str
    type_: str = Field(alias="type")
    form: Optional[list["Form"]] = []


class Citation(BaseModel):
    bibl: list[dict]
    type_: str = Field(alias="type")
    quote: Optional[str] = None
    xml_id: str = Field(alias="xmlId")
    note: Optional[list[dict]] = []


class Sense(BaseModel):
    n: Optional[str] = None
    def_: str = Field(alias="def")
    sense: list["Sense"] = []
    cit: Optional[list[Citation]] = []
    usg: Optional[list[dict]] = []
    xml_id: str = Field(alias="xmlId")
    entry: Optional[list[dict]] = []


class EtymologySegment(BaseModel):
    type_: str = Field(alias="type")
    value: str
    target: Optional[str] = None
    unit: Optional[str] = None
    content: Optional[list["EtymologySegment"]] = []
    rend: Optional[str] = None


class Etymology(BaseModel):
    content: list[EtymologySegment]
    ref: Optional[list[dict]] = []


class GrammarFeature(BaseModel):
    text: str
    type_: str = Field(alias="type")


class GrammarGroup(BaseModel):
    gram: list[GrammarFeature]


class BiblItem(BaseModel):
    note: list[dict]
    title: dict
    bibl_scope: dict = Field(alias="biblScope")


class ListBibl(BaseModel):
    bibl: list
    head: str
    type_: str = Field(alias="type")


class CrossReference(BaseModel):
    ref: list
    type_: Optional[str] = Field(alias="type")
    subtype: Optional[str]


class Entry(BaseModel):
    etym: Optional[Etymology] = None
    form: list[Form]
    sense: list[Sense]
    xml_id: str = Field(alias="xmlId")
    xml_lang: str = Field(alias="xmlLang")
    gram_grp: GrammarGroup = Field(alias="gramGrp")
    list_bibl: ListBibl = Field(alias="listBibl")
    xr: Optional[CrossReference] = None
