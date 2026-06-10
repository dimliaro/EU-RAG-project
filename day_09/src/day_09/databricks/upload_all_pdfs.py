import argparse
from collections import Counter
from pathlib import Path

from day_09.config import DATA_DIR, RAW_PDF_VOLUME_DIR
from day_09.databricks.volume_uploader import upload_to_volume

VOLUME_DIR = RAW_PDF_VOLUME_DIR

SUPPORTED = {".pdf"}


def _document_id(path: Path) -> str:
    return path.stem


def main():
    parser = argparse.ArgumentParser(
        description="Upload local regulatory PDFs to the configured Databricks Volume."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print upload plan without writing to the Databricks Volume.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace existing files in the Databricks Volume.",
    )
    args = parser.parse_args()

    files = [
        path for path in DATA_DIR.iterdir()
        if path.suffix.lower() in SUPPORTED
    ]

    print(f"Found {len(files)} local PDF files:")
    for path in files:
        volume_path = f"{VOLUME_DIR}/{path.name}"
        print(f" - {path.name} -> {volume_path}")

    filename_counts = Counter(path.name for path in files)
    document_id_counts = Counter(_document_id(path) for path in files)
    duplicate_filenames = [name for name, count in filename_counts.items() if count > 1]
    duplicate_document_ids = [
        document_id for document_id, count in document_id_counts.items() if count > 1
    ]

    if duplicate_filenames:
        print(f"Duplicate filenames detected: {duplicate_filenames}")
    if duplicate_document_ids:
        print(f"Duplicate document_ids detected: {duplicate_document_ids}")

    if args.dry_run:
        print("Dry run only. No files uploaded.")
        return

    for path in files:
        volume_path = f"{VOLUME_DIR}/{path.name}"
        upload_to_volume(path, volume_path, overwrite=args.overwrite)

    print("Upload complete.")


if __name__ == "__main__":
    main()
