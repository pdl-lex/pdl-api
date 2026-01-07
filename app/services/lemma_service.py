import os
import re
from typing import Optional

from fastapi import HTTPException
from pymongo import MongoClient

from app.models import DisplayEntry, DisplayEntryList, Entry, Resource


def _build_lemma_query(lemma: str) -> dict:
    if pattern_match := re.match(r"^/([^/]+)/([imxs]*)?$", lemma):
        pattern = pattern_match.group(1)
        flags = pattern_match.group(2) or ""
        return {"headword.lemma": {"$regex": pattern, "$options": flags}}
    else:
        return {"headword.lemma": lemma}


dispatcher = {
    "term": lambda args: {"$text": {"$search": args["term"]}},
    "lemma": lambda args: _build_lemma_query(args["lemma"]),
    "resources": lambda args: {"source": {"$in": [s.value for s in args["resources"]]}},
    "pos": lambda args: {"pos": args["pos"]},
    "npos": lambda args: {"nPos": args["npos"]},
}


def _build_query(**kwargs) -> dict:
    query = {}

    for key, func in dispatcher.items():
        if key in kwargs and kwargs[key] is not None:
            query = {**query, **func(kwargs)}

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
        **filters,
    ) -> DisplayEntryList:
        query = _build_query(term=term, **filters)

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
