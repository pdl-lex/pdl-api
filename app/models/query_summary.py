from typing import Optional

from pydantic import Field

from app.models.base import BaseModel
from app.models.entry import GrammaticalFeatures, Headword, ResourceName


class LemmaInfo(BaseModel, GrammaticalFeatures):
    headword: Headword
    source_id: str = Field(alias="sourceId")
    lex_id: str = Field(alias="lexId")
    source: ResourceName
    main_senses: Optional[list[str]] = Field(alias="mainSenses", default=[])


class ResourceCount(BaseModel):
    source: ResourceName
    count: int


class QuerySummary(BaseModel):
    total: int
    counts_by_resource: list[ResourceCount] = Field(alias="countsByResource")
    items: list[LemmaInfo] = []
