from typing import Optional

from pydantic import Field

from app.models.base import BaseModel
from app.models.entry import GrammaticalFeatures, Headword, Resource, Sense


class LemmaPreview(BaseModel, GrammaticalFeatures):
    headword: Headword
    xml_id: str = Field(alias="xml:id")
    source: Resource
    flat_senses: Optional[list[Sense]] = Field(alias="flatSenses", default=[])


class QuerySummary(BaseModel):
    total: int
    counts_by_resource: dict[Resource, int] = Field(alias="countsByResource")
    lemma_previews: Optional[list[LemmaPreview]] = Field(
        alias="lemmaPreviews", default=None
    )
