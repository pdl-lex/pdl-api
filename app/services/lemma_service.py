import os

from pymongo import MongoClient


class LemmaService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["wb"]
        self.collection = self.db["bwb"]

    def query_lemma(self, lemma: str) -> dict:
        result = self.collection.find_one({"entry.form.orth": lemma})

        return result.get("entry") if result else {"error": "Lemma not found"}
