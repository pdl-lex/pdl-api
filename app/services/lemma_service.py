import os
from typing import Optional

from fastapi import HTTPException
from pymongo import MongoClient

from app.models import DisplayEntry, DisplayEntryList, Entry, Resource


def _filter_by_resources(query: dict, resources: Optional[list[Resource]]) -> dict:
    if resources:
        return {**query, "source": {"$in": [s.value for s in resources]}}
    return query


class LemmaService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.entries = self.db.get_collection("entries")
        self.display = self.db.get_collection("display")

    def free_text_search(
        self,
        term: str,
        page: int,
        results_per_page: int,
        resources: Optional[list[Resource]] = None,
    ) -> DisplayEntryList:
        query = _filter_by_resources({"$text": {"$search": term}}, resources)

        pipeline = [
            {"$match": query},
            {"$project": {"_id": False}},
            {
                "$facet": {
                    "items": [
                        {"$skip": (page - 1) * results_per_page},
                        {"$limit": results_per_page},
                    ],
                    "total": [{"$count": "count"}],
                }
            },
            {
                "$addFields": {
                    "total": {"$ifNull": [{"$first": "$total.count"}, 0]},
                    "page": {"$literal": page},
                    "itemsPerPage": {"$literal": results_per_page},
                }
            },
        ]

        return next(self.display.aggregate(pipeline))

    def fetch_lemma(self, lemma_id: str) -> Entry:
        result = self.entries.find_one({"entry.xml:id": lemma_id})

        if result is None:
            raise HTTPException(status_code=404, detail=f"Unknown id: {lemma_id!r}")

        return result["entry"]

    def fetch_lemma_display(self, lemma_id: str) -> DisplayEntry:
        result = self.display.find_one({"xml:id": lemma_id}, projection={"_id": False})

        if result is None:
            raise HTTPException(status_code=404, detail=f"Unknown id: {lemma_id!r}")

        return result
