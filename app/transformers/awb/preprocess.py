"""Replace the undeclared named entities in the raw AWB XML with Unicode characters.

The AWB XML (TCDH retro-digitization) uses HTML and TCDH-specific entities without
a DTD, so it cannot be parsed. HTML entities are resolved via the standard library,
TCDH-specific ones via entity_mapping.csv. The XML built-ins (&amp; &lt; &gt; &quot;
&apos;) are kept. Unknown entities abort the run.
"""

import csv
import html.entities
import re
from pathlib import Path

import lxml.etree as ET  # noqa: N812

AWB_DIR = Path(__file__).parent
RAW_DIR = AWB_DIR / "raw"
DATA_DIR = AWB_DIR / "data"
MAPPING_PATH = AWB_DIR / "entity_mapping.csv"

XML_BUILTIN_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}
ENTITY_PATTERN = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")


def load_mapping(path: Path) -> dict[str, str]:
    """Read entity_mapping.csv and turn 'U+006F U+036E' into the actual characters."""
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return {
            row["entity"]: "".join(
                chr(int(cp.removeprefix("U+"), 16)) for cp in row["codepoints"].split()
            )
            for row in reader
        }


def replace_entities(text: str, mapping: dict[str, str]) -> tuple[str, set[str]]:
    """Return the text with entities replaced and the set of unknown entity names."""
    unknown = set()

    def resolve(match: re.Match) -> str:
        name = match.group(1)
        if name in XML_BUILTIN_ENTITIES:
            return match.group(0)
        if name in mapping:
            return mapping[name]
        if f"{name};" in html.entities.html5:
            return html.entities.html5[f"{name};"]
        unknown.add(name)
        return match.group(0)

    return ENTITY_PATTERN.sub(resolve, text), unknown


def preprocess(raw_dir: Path, data_dir: Path, mapping_path: Path):
    mapping = load_mapping(mapping_path)
    data_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(raw_dir.glob("*.xml"))
    unknown_by_file = {}
    for filepath in files:
        text, unknown = replace_entities(filepath.read_text(encoding="utf-8"), mapping)
        if unknown:
            unknown_by_file[filepath.name] = sorted(unknown)
            continue

        # fail early if the result is still not well-formed XML
        ET.fromstring(text.encode("utf-8"))
        (data_dir / filepath.name).write_text(text, encoding="utf-8")

    if unknown_by_file:
        details = "\n".join(
            f"  {f}: {', '.join(e)}" for f, e in unknown_by_file.items()
        )
        raise ValueError(
            f"Unknown entities, add them to {mapping_path.name}:\n{details}"
        )

    print(f"Wrote {len(files)} files to {data_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Replace named entities in raw AWB XML with Unicode"
    )
    parser.add_argument(
        "-i", "--input", help="Raw XML folder", type=Path, default=RAW_DIR
    )
    parser.add_argument(
        "-o", "--out", help="Output folder", type=Path, default=DATA_DIR
    )
    parser.add_argument(
        "-m", "--mapping", help="Entity mapping CSV", type=Path, default=MAPPING_PATH
    )
    args = parser.parse_args()

    preprocess(args.input, args.out, args.mapping)


# run with
# uv run python -m app.transformers.awb.preprocess
