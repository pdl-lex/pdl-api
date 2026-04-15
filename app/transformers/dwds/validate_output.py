from pathlib import Path

from app.models.entry import Entry
from app.transformers.dwds.dwds_transformer import DwdsXmlTransformer

t = DwdsXmlTransformer()
for f in Path("app/transformers/dwds/data").glob("*.xml"):
    data = t.transform(f)
    Entry.model_validate(data)
    print(f"{f.name}: OK")


# run with
# uv run python -m app.transformers.dwds.validate_output
