from datetime import date
from enum import Enum

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import Field, SQLModel


class Resource(str, Enum):
    BDO = "bdo"
    BWB = "bwb"
    DIBS = "dibs"
    WBF = "wbf"
    DWDS = "dwds"


class BaseModel(SQLModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class EntryModel(BaseModel, table=True):
    id: str | None = None
    original_id: str | None = None
    lemma: str
    lemma_index: int | None = Field(default=None)
    index_letter: str = Field(min_length=1, max_length=1, default="-")
    retrieved_at: date | None = None
    uploaded_at: date | None = None
    resource: Resource
    resource_url: str | None = None
    original_resource: str | None = None

    original_gender: str | None = None
    original_pos: str | None = None
    original_number: str | None = None
    gender: str | None = None
    pos: str | None = None
    number: str | None = None
