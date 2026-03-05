from pydantic import Field

from app.models.base import BaseModel


class ToolImage(BaseModel):
    url: str
    alt_text: str = Field(alias="altText")


class ToolDetails(BaseModel):
    title: str
    body: str
    images: list[ToolImage] | None = None


class Tool(BaseModel):
    title: str
    teaser: str
    image_url: str | None = Field(alias="imageUrl", default=None)
    tool_url: str | None = Field(alias="toolUrl", default=None)
    details: ToolDetails | None = None
