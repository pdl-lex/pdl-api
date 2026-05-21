from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel

from app.models.entry import GrammaticalFeatures, Headword, Resource


class LemmaInfo(SQLModel, GrammaticalFeatures):
    headword: Headword
    source_id: str = Field(alias="sourceId")
    lex_id: str = Field(alias="lexId")
    source: Resource
    main_senses: Optional[list[str]] = Field(alias="mainSenses", default=[])


class ResourceCount(SQLModel):
    source: Resource
    count: int


class QuerySummary(SQLModel):
    total: int
    counts_by_resource: list[ResourceCount] = Field(alias="countsByResource")
    items: list[LemmaInfo] = []
