import os
import re

from fastapi import HTTPException
from pymongo import MongoClient

from app.models.entry import DisplayEntry, DisplayEntryList, Entry
from app.models.query_summary import QuerySummary
from app.transformers.standoff.span_accumulator import SpanAccumulator


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

    def _convert_spans_to_display(self, result: DisplayEntryList):
        for index, item in enumerate(result["items"]):
            if (etym := item.get("etym")) is not None:
                etym = SpanAccumulator(etym).to_display()
                result["items"][index]["etym"] = etym

        return result

    def free_text_search(
        self,
        term: str,
        page: int,
        results_per_page: int,
        **filters,
    ) -> DisplayEntryList:
        pipeline = [
            {"$match": _build_query(term=term, **filters)},
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

        return self._convert_spans_to_display(next(self.display.aggregate(pipeline)))

    def query_summary(
        self,
        term: str,
        **filters,
    ) -> QuerySummary:
        pipeline = [
            {"$match": _build_query(term=term, **filters)},
            {"$project": {"_id": False}},
            {
                "$facet": {
                    "lemmaGroups": [
                        {
                            "$project": {
                                "headword": 1,
                                "xml:id": 1,
                                "source": 1,
                                "mainSenses": "$sense.def",
                            },
                        },
                        {
                            "$group": {
                                "_id": "$headword.lemma",
                                "items": {"$addToSet": "$$ROOT"},
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "lemma": "$_id",
                                "items": "$items",
                                "length": {"$size": "$items"},
                            }
                        },
                        {"$sort": {"length": -1}},
                        {"$unset": "length"},
                        {"$limit": 100},
                    ],
                    "total": [
                        {
                            "$count": "count",
                        },
                    ],
                    "countsByResource": [
                        {
                            "$group": {
                                "_id": "$source",
                                "count": {"$sum": 1},
                            },
                        },
                        {
                            "$project": {
                                "source": "$_id",
                                "_id": "$$REMOVE",
                                "count": {"$ifNull": ["$count", 0]},
                            }
                        },
                    ],
                }
            },
            {"$addFields": {"total": {"$ifNull": [{"$first": "$total.count"}, 0]}}},
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
