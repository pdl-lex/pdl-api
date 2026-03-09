import os
import re

from pymongo import MongoClient

from app.models.tool import Tool


class ToolService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.tools = self.db.get_collection("tools")

    def list(self):
        return list(self.tools.find({}, projection={"_id": False}))

    def add(self, tool: Tool):
        self.tools.insert_one({**tool.model_dump(by_alias=True), "_id": tool.title})

    def delete(self, tool_id: str):
        result = self.tools.delete_one({"_id": tool_id})
        return result.deleted_count > 0
