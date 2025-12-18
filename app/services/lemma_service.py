import os

from fastapi import HTTPException
from pymongo import MongoClient

from app.models import Entry


class LemmaService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.collection = self.db["entries"]

    def free_text_search(self, query: str) -> list[Entry]:
        results = self.collection.find({"$text": {"$search": query}})

        return [result.get("entry") for result in results]

    def fetch_lemma(self, lemma_id: str) -> Entry:
        result = self.collection.find_one({"entry.xml:id": lemma_id})
        if result is None:
            raise HTTPException(status_code=404, detail=f"Unknown id: {lemma_id!r}")

        return result["entry"]
