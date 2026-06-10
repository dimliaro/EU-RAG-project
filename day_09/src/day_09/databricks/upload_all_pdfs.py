from pathlib import Path

from day_09.config import DATA_DIR, RAW_PDF_VOLUME_DIR
from day_09.databricks.volume_uploader import upload_to_volume

VOLUME_DIR = RAW_PDF_VOLUME_DIR

SUPPORTED = {".pdf", ".csv", ".docx", ".txt"}


def main():
    files = [
        path for path in DATA_DIR.iterdir()
        if path.suffix.lower() in SUPPORTED
    ]

    print(f"Found {len(files)} local files:")
    for path in files:
        print(f" - {path.name}")

    for path in files:
        volume_path = f"{VOLUME_DIR}/{path.name}"
        upload_to_volume(path, volume_path)

    print("Upload complete.")


if __name__ == "__main__":
    main()
