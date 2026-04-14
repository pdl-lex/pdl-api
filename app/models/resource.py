from enum import Enum
from typing import Optional

from app.models.base import BaseModel


class ResourceName(Enum):
    BDO = "bdo"
    BWB = "bwb"
    DIBS = "dibs"
    WBF = "wbf"
    DWDS = "dwds"


class Resource(BaseModel):
    name: ResourceName
    credits: Optional[str] = None
    license: Optional[str] = None
