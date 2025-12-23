import os

from pydantic import TypeAdapter
from pymongo import ASCENDING, IndexModel, MongoClient

from app.models import DisplayEntry

fulltext_search_fields = ["headword", "flatSenses.def"]
index_fields = [
    "source",
    "xml:id",
    "headword",
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
            [(field, "text") for field in fulltext_search_fields], name="fulltextIndex"
        )

        self.display.create_indexes(
            [IndexModel([(field, ASCENDING)]) for field in index_fields]
        )

    def insert_display_data(self, data: list[DisplayEntry]):
        self._reset_display_collection()

        display_entry_list = TypeAdapter(list[DisplayEntry])
        dump = display_entry_list.dump_python(data, by_alias=True, mode="json")

        self.display.insert_many(dump)

        self._create_indexes()
