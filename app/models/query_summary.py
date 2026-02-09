from typing import Optional

from pydantic import Field

from app.models.base import BaseModel
from app.models.entry import GrammaticalFeatures, Headword, Resource


class LemmaInfo(BaseModel, GrammaticalFeatures):
    headword: Headword
    xml_id: str = Field(alias="xml:id")
    source: Resource
    main_senses: Optional[list[str]] = Field(alias="mainSenses", default=[])


class ResourceCount(BaseModel):
    source: Resource
    count: int


class QuerySummary(BaseModel):
    total: int
    counts_by_resource: list[ResourceCount] = Field(alias="countsByResource")
    items: list[LemmaInfo] = []
