from enum import Enum

from pydantic import BaseModel


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
