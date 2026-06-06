"""
data_fetcher.py
Downloads a file from a URL or API endpoint to a local directory.
Supports any file type — the extension is preserved from the URL.
"""

import requests
from pathlib import Path


def fetch_file(url: str, dest_dir: str | Path = "/tmp", headers: dict | None = None) -> Path:
    """
    Download a file from a URL to dest_dir.

    Args:
        url:      Direct file URL or API endpoint that returns a file.
        dest_dir: Local directory to save the file.
        headers:  Optional auth headers (e.g. {"Authorization": "Bearer <token>"}).

    Returns:
        Local Path of the downloaded file.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0] or "download"
    local_path = dest_dir / filename

    response = requests.get(url, headers=headers or {}, stream=True, timeout=60)
    response.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Downloaded: {local_path} ({local_path.stat().st_size // 1024} KB)")
    return local_path
