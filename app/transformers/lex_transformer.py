from datetime import date
from functools import partial
from pathlib import Path

from tqdm.contrib.concurrent import process_map

from app.transformers.base_xml_transformer import BaseXmlTransformer
from app.transformers.bdo.bdo_transformer import BdoXmlTransformer
from app.transformers.dwds.dwds_transformer import DwdsXmlTransformer

OUTPUT_DATA_DIR = Path("data/lexoterm")
OUTPUT_ERROR_DIR = Path("data/lexoterm")
TRANSFORMER_REGISTRY: dict[str, type[BaseXmlTransformer]] = {
    "bdo": BdoXmlTransformer,
    "dwds": DwdsXmlTransformer,
}


def ensure_output_directories():
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ERROR_DIR.mkdir(parents=True, exist_ok=True)


def create_id(namespace: str, source_dir: Path, filepath: Path | str):
    subpath = Path(filepath).relative_to(source_dir).with_suffix("")
    return f"{namespace}:{subpath}"


def _process_single_file(
    filepath: Path,
    resource_name: str,
    xml_dir: Path,
    retrieved_at: date | None = None,
) -> dict:
    """Process a single XML file."""
    Transformer = TRANSFORMER_REGISTRY[resource_name]()  # noqa: N806
    result = Transformer.transform(filepath)
    result["lexId"] = create_id(
        namespace=resource_name, source_dir=xml_dir, filepath=filepath
    )

    if retrieved_at is not None:
        result["retrievedAt"] = retrieved_at.isoformat()

    return result


def transform(
    xml_dir: Path,
    resource_name: str,
    *,
    retrieved_at: date | None = None,
    num_workers: int | None = None,
) -> list[dict]:
    """Transform XML files to LexoTerm format with multiprocessing.

    Args:
        xml_dir: Directory containing XML files
        resource_name: Name of the resource transformer to use
        retrieved_at: Optional retrieval date
        num_workers: Number of worker processes. Defaults to CPU count.
                    Set to 1 to disable multiprocessing.
    """
    files = list(xml_dir.rglob("*.xml"))
    worker_fn = partial(
        _process_single_file,
        resource_name=resource_name,
        xml_dir=xml_dir,
        retrieved_at=retrieved_at,
    )
    chunksize = 100

    return process_map(
        worker_fn,
        files,
        max_workers=num_workers,
        chunksize=chunksize,
        desc="Converting XML to LexoTerm format",
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Convert lexical resources to LexoTerm JSON"
    )
    parser.add_argument(
        "resource", help="Resource name", choices=list(TRANSFORMER_REGISTRY)
    )
    parser.add_argument(
        "-p", "--path", help="Path to source folder", required=True, type=Path
    )
    parser.add_argument(
        "-o", "--out", help="Path to output file (jsonl-format)", type=Path
    )
    parser.add_argument(
        "--retrieved-at",
        help="Retrieval data (iso format, e.g. '2026-04-23')",
        type=date.fromisoformat,
    )

    args = parser.parse_args()

    result = transform(args.path, args.resource, retrieved_at=args.retrieved_at)

    ensure_output_directories()

    output_path = (
        OUTPUT_DATA_DIR / f"{args.resource}.jsonl" if args.out is None else args.out
    )

    with open(output_path, "w", encoding="utf-8") as json_file:
        for entry in result:
            print(json.dumps(entry, ensure_ascii=False), file=json_file)

    print(f"Stored data in {output_path}")
