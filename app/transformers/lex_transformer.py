from pathlib import Path

from tqdm import tqdm

from app.transformers.bdo.bdo_transformer import BdoXmlTransformer

OUTPUT_DATA_DIR = Path("data/lexoterm")
OUTPUT_ERROR_DIR = Path("data/lexoterm")


def ensure_output_directories():
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ERROR_DIR.mkdir(parents=True, exist_ok=True)


def bdo_to_lexoterm(bdo_dir: Path) -> list[dict]:
    files = list(bdo_dir.rglob("*.xml"))
    result = []
    report_data = {}
    bdo_transformer = BdoXmlTransformer()
    progress_bar = tqdm(files, desc="Converting BDO XML to LexoTerm format")

    for path in progress_bar:
        progress_bar.set_description(f"Processing {path.parent.parent.name}")

        transformed = bdo_transformer.transform(path)
        result.append(transformed)

        report_data[str(path)] = bdo_transformer.report_data

    return result, report_data


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

    args = parser.parse_args()

    dispatch = {
        "bdo": bdo_to_lexoterm,
        "dwds": dwds_to_lexoterm,
    }

    result, report_data = dispatch[args.resource](args.path)

    ensure_output_directories()

    output_path = OUTPUT_DATA_DIR / f"{args.resource}.json"
    report_path = OUTPUT_DATA_DIR / f"{args.resource}_report.json"

    with open(output_path, "w") as json_file:
        json.dump(result, json_file, ensure_ascii=False, indent=2)

    with open(report_path, "w") as json_file:
        json.dump(report_data, json_file, ensure_ascii=False, indent=2)

    print(f"Stored data in {output_path}.")
    print(f"See {report_path} for coverage details.")
