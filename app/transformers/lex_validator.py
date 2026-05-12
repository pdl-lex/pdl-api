import csv
from pathlib import Path

from pydantic import ValidationError

from app.models.entry import Entry


def validate_jsonl(filepath):
    errors = []

    with open(filepath) as f:
        total = sum(1 for _ in f)
        f.seek(0)

        for index, line in tqdm(enumerate(f, start=1), total=total):
            if not line.strip():
                continue
            try:
                Entry.model_validate_json(line, by_alias=True)
            except ValidationError as err:
                errors.append((index, str(err), line[:50] + "[...]"))

    return errors


if __name__ == "__main__":
    import argparse

    from tqdm import tqdm

    parser = argparse.ArgumentParser(description="Validate JSONL data")
    parser.add_argument("path", help="Path to JSONL-file to validate", type=Path)
    parser.add_argument(
        "--errorfile",
        help="Path to error summary (tsv)",
        default="validation_errors.tsv",
    )

    args = parser.parse_args()

    errors = validate_jsonl(args.path)

    if len(errors) == 0:
        print("All clear!")
    else:
        with open(args.errorfile, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["line", "error", "sample"])
            writer.writerows(errors)

        print(f"Found {len(errors)} errors (see {args.errorfile} for details)")
