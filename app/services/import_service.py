import os

from dotenv import load_dotenv
from pydantic import TypeAdapter
from pymongo import ASCENDING, IndexModel, MongoClient

from app.models.entry import Entry

load_dotenv()

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
    "headword.lemma",
    "pos",
    "gender",
    "number",
]


class ImportService:
    def __init__(self):
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client["lex"]
        self.display = self.db.get_collection("display")

    def _reset_display_collection(self):
        self.display.delete_many({})
        self.display.drop_indexes()

    def _create_indexes(self):
        self.display.create_index(
            [(field["key"], "text") for field in fulltext_search_fields],
            name="fulltextIndex",
            weights={field["key"]: field["weight"] for field in fulltext_search_fields},
        )

        self.display.create_indexes(
            [IndexModel([(field, ASCENDING)]) for field in index_fields]
        )

    def insert_display_data(self, data: list[Entry]):
        self._reset_display_collection()

        display_entry_list = TypeAdapter(list[Entry])
        dump = display_entry_list.dump_python(data, by_alias=True, mode="json")

        result = self.display.insert_many(
            [{**entry, "_id": entry["lexId"]} for entry in dump]
        )

        self._create_indexes()

        return {
            "inserted_count": len(result.inserted_ids),
            "inserted_ids": result.inserted_ids,
        }


if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path

    import requests
    from requests.exceptions import ConnectionError
    from rich.console import Console
    from rich.prompt import Confirm

    parser = argparse.ArgumentParser(
        description="Import display entry data into the LexoTerm MongoDB instance"
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

    API_KEY = os.environ["MONGO_API_KEY"]
    console = Console()

    if args.production and not Confirm.ask(
        "[bold red]⚠️  You are about to write to the PRODUCTION database. This will overwrite existing data. Are you sure?",
        default=False,
    ):
        console.print("[yellow]Operation cancelled.")
        sys.exit(0)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    with console.status(f"[bold green]Sending data to {URL}...") as status:
        try:
            response = requests.post(
                f"{URL.rstrip('/')}/insert-display-data",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
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
