import gzip
import os
from io import BytesIO
from itertools import islice
from string import ascii_uppercase
from typing import Iterable

from dotenv import load_dotenv
from pydantic import TypeAdapter
from pymongo import ASCENDING, IndexModel, MongoClient
from unidecode import unidecode

from app.models.entry import BDO_RESOURCES, Entry, Resource

load_dotenv()

ALPHABET = set(ascii_uppercase) | {"-"}

fulltext_search_fields = [
    {"key": "headword.lemma", "weight": 10},
    {"key": "flatSenses.def", "weight": 1},
    {"key": "flatSenses.cit.quote", "weight": 1},
    {"key": "etym.text", "weight": 1},
    {"key": "family", "weight": 1},
    {"key": "derivations.text", "weight": 1},
]
index_fields = [
    "source",
    "sourceId",
    "lexId",
    "indexLetter",
    "headword.lemma",
    "pos",
    "gender",
    "number",
]


def batched(iterable, n):
    "Batch data into lists of length n. The last batch may be shorter."
    it = iter(iterable)
    while True:
        batch = tuple(islice(it, n))
        if not batch:
            return
        yield batch


class ImportService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.entries = self.db.get_collection("entries")

    def _drop_entries(self, resource: Resource):
        if resource == Resource.BDO:
            self.entries.delete_many(
                {"source": {"$in": [r.value for r in BDO_RESOURCES]}}
            )
        else:
            self.entries.delete_many({"source": resource.value})
        self.entries.drop_indexes()

    def create_indexes(self, drop=False):
        if drop:
            self.entries.drop_indexes()
        self.entries.create_index(
            [(field["key"], "text") for field in fulltext_search_fields],
            name="fulltextIndex",
            weights={field["key"]: field["weight"] for field in fulltext_search_fields},
        )

        self.entries.create_indexes(
            [IndexModel([(field, ASCENDING)]) for field in index_fields]
        )

    def _extract_index_letter(self, lemma: str) -> str:
        normalized_letter = unidecode(lemma[0]).upper()
        assert len(normalized_letter) == 1

        return normalized_letter if normalized_letter in ALPHABET else "#"

    def insert_data(self, data: Iterable[dict], resource: Resource, batch_size=100):
        self._drop_entries(resource)

        def ensure_valid(item: dict):
            Entry.model_validate(item, by_alias=True)
            return item

        inserted_count = 0

        for batch in batched(data, n=batch_size):
            result = self.entries.insert_many(
                (
                    {
                        **ensure_valid(entry),
                        "_id": entry["lexId"],
                        "indexLetter": self._extract_index_letter(
                            entry["headword"]["lemma"]
                        ),
                    }
                    for entry in batch
                ),
                ordered=False,
            )
            inserted_count += len(result.inserted_ids)

        self.create_indexes()

        return {
            "inserted_count": inserted_count,
        }


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    import requests
    from requests.exceptions import ConnectionError
    from rich.console import Console
    from rich.prompt import Confirm

    parser = argparse.ArgumentParser(
        description="Import dictionaries into the LexoTerm MongoDB instance"
    )
    parser.add_argument(
        "resource", help="Target resource name", choices=["bdo", "dwds"]
    )
    parser.add_argument(
        "--production", help="Write to production db", action="store_true"
    )
    parser.add_argument(
        "--api-url",
        help="URL to FastAPI instance (overrides --production)",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument("filepath", help="Path to source json")

    args = parser.parse_args()
    filepath = Path(args.filepath).resolve()

    URL = os.environ["LEXOTERM_API_URL"] if args.production else args.api_url

    API_KEY = os.environ["API_UPLOAD_KEY"]
    console = Console()

    if args.production and not Confirm.ask(
        (
            "[bold red]⚠️ You are about to write to the PRODUCTION database. "
            f"This will overwrite existing {args.resource} data. Are you sure?"
        ),
        default=False,
    ):
        console.print("[yellow]Operation cancelled.")
        sys.exit(0)

    with (
        console.status(f"Compressing data...") as status,
        open(filepath, "rb") as f,
    ):
        data = BytesIO(gzip.compress(f.read()))

    with console.status(f"Sending data to {URL}...") as status:
        try:
            files = {"file": ("bdo.jsonl", data, "application/jsonl")}
            response = requests.post(
                f"{URL.rstrip('/')}/upload?resource={args.resource}",
                files=files,
                headers={
                    "X-API-Key": API_KEY,
                    "Content-Encoding": "gzip",
                },
            )
        except ConnectionError as err:
            console.print(
                f"[bold red]❌ Could not reach API – is the url {URL} correct and online?\n"
            )
            raise err

    if response.status_code == 200:
        result = response.json()
        console.log(
            f"[bold green]✅ {result['inserted_count']} documents inserted successfully."
        )
    else:
        console.print(f"[bold red]❌ Error: {response.status_code}")
        console.print(response.text)
