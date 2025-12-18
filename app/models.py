from enum import Enum
from typing import Optional

from pydantic import BaseModel as DefaultModel
from pydantic import ConfigDict, Field


class Resource(Enum):
    BWB = "bwb"
    DIBS = "dibs"
    WBF = "wbf"


class BaseModel(DefaultModel):
    model_config = ConfigDict(extra="forbid")


class Form(BaseModel):
    orth: Optional[str] = ""
    type_: str = Field(alias="type")
    form: Optional[list["Form"]] = []


class Citation(BaseModel):
    bibl: Optional[list[dict]] = []
    type_: str = Field(alias="type")
    quote: Optional[str] = None
    xml_id: str = Field(alias="xml:id")
    note: Optional[list[dict]] = []


class Sense(BaseModel):
    n: Optional[str] = None
    def_: Optional[str] = Field(alias="def", default="")
    sense: list["Sense"] = []
    cit: Optional[list[Citation]] = []
    usg: Optional[list[dict]] = []
    xml_id: str = Field(alias="xml:id")
    entry: Optional[list[dict]] = []


class EtymologySegment(BaseModel):
    type_: str = Field(alias="type")
    value: str
    target: Optional[str] = None
    unit: Optional[str] = None
    content: Optional[list["EtymologySegment"]] = []
    rend: Optional[str] = None


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
    subtype: Optional[str]


class Entry(BaseModel):
    etym: Optional[list[Etymology] | list[str]] = []
    form: list[Form]
    sense: Optional[list[Sense]] = []
    xml_id: str = Field(alias="xml:id")
    xml_lang: str = Field(alias="xml:lang")
    gram_grp: Optional[list[GrammarGroup]] = Field(alias="gramGrp", default=None)
    list_bibl: Optional[ListBibl] = Field(alias="listBibl", default=None)
    xr: Optional[list[CrossReference]] = []
