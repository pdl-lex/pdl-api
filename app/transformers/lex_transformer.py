from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from os import cpu_count
from pathlib import Path
from typing import Iterator, Optional

from tqdm import tqdm

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
) -> Iterator[dict]:
    """Transform XML files to LexoTerm format with optional multiprocessing.

    Args:
        xml_dir: Directory containing XML files
        resource_name: Name of the resource transformer to use
        retrieved_at: Optional retrieval date
        num_workers: Number of worker processes. Defaults to CPU count.
                    Set to 1 to disable multiprocessing.
    """
    files = list(xml_dir.rglob("*.xml"))

    if num_workers is None:
        num_workers = cpu_count() or 4

    if num_workers == 1:
        progress_bar = tqdm(files, desc="Converting XML to LexoTerm format")
        for filepath in progress_bar:
            progress_bar.set_description(f"Processing {filepath.parent.parent.name}")
            result = _process_single_file(
                filepath, resource_name, xml_dir, retrieved_at
            )
            yield result
    else:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            progress_bar = tqdm(
                total=len(files), desc="Converting XML to LexoTerm format"
            )

            futures = {
                executor.submit(
                    _process_single_file, filepath, resource_name, xml_dir, retrieved_at
                ): filepath
                for filepath in files
            }

            for future in as_completed(futures):
                filepath = futures[future]
                progress_bar.set_description(
                    f"Processing {filepath.parent.parent.name}"
                )
                result = future.result()
                progress_bar.update(1)
                yield result


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
