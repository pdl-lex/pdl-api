import os
from typing import Optional

from fastapi import HTTPException
from pymongo import MongoClient

from app.models import Entry, Resource


class LemmaService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.entries = self.db["entries"]

    def free_text_search(
        self, term: str, resource: Optional[list[Resource]] = None
    ) -> list[Entry]:
        query = {"$text": {"$search": term}}
        if resource:
            query["src"] = {"$in": [s.value for s in resource]}

        print(self.entries.count_documents(query))
        results = self.entries.find(query)

        return [result.get("entry") for result in results]

    def fetch_lemma(self, lemma_id: str) -> Entry:
        result = self.entries.find_one({"entry.xml:id": lemma_id})
        if result is None:
            raise HTTPException(status_code=404, detail=f"Unknown id: {lemma_id!r}")

        return result["entry"]
