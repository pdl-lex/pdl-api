import os

from pymongo import MongoClient


class ToolService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.tools = self.db.get_collection("tools")

    def get_tools(self):
        return list(self.tools.find({}, projection={"_id": False}))
