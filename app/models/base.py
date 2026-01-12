from pydantic import BaseModel as DefaultModel
from pydantic import ConfigDict


class BaseModel(DefaultModel):
    model_config = ConfigDict(extra="forbid")
