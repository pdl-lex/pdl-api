from pathlib import Path
from typing import Generator

from tqdm import tqdm

from app.transformers.bdo.bdo_transformer import BdoXmlTransformer

OUTPUT_DATA_DIR = Path("data/lexoterm")
OUTPUT_ERROR_DIR = Path("data/lexoterm")


def ensure_output_directories():
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ERROR_DIR.mkdir(parents=True, exist_ok=True)


def bdo_to_lexoterm(bdo_dir: Path) -> Generator[dict]:
    files = list(bdo_dir.rglob("*.xml"))
    bdo_transformer = BdoXmlTransformer()
    progress_bar = tqdm(files, desc="Converting BDO XML to LexoTerm format")

    for path in progress_bar:
        progress_bar.set_description(f"Processing {path.parent.parent.name}")

        yield bdo_transformer.transform(path)


def dwds_to_lexoterm(dwds_dir: Path):
    raise NotImplementedError()


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Convert lexical resources to LexoTerm JSON"
    )
    parser.add_argument("resource", help="Resource name", choices=["bdo", "dwds"])
    parser.add_argument(
        "-p", "--path", help="Path to source folder", required=True, type=Path
    )
    parser.add_argument(
        "-o", "--out", help="Path to output file (jsonl-format)", type=Path
    )

    args = parser.parse_args()

    dispatch = {
        "bdo": bdo_to_lexoterm,
        "dwds": dwds_to_lexoterm,
    }

    result = dispatch[args.resource](args.path)

    ensure_output_directories()

    output_path = (
        OUTPUT_DATA_DIR / f"{args.resource}.jsonl" if args.out is None else args.out
    )

    with open(output_path, "w") as json_file:
        for entry in result:
            print(json.dumps(entry, ensure_ascii=False), file=json_file)

    print(f"Stored data in {output_path}")
