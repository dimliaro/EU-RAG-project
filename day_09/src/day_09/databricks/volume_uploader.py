"""
Uploads a local file to a Databricks Unity Catalog Volume using the Databricks SDK.

Volume path format: /Volumes/<catalog>/<schema>/<volume_name>/<filename>
"""

from pathlib import Path
from databricks.sdk import WorkspaceClient


def upload_to_volume(
    local_path: str | Path,
    volume_path: str,
    overwrite: bool = False,
) -> str:
    """
    Upload a local file to a Databricks Unity Catalog Volume.

    Args:
        local_path:   Path to the local file (any type: PDF, TXT, CSV...).
        volume_path:  Destination path on Databricks, e.g.
                      /Volumes/main/rag/files/document.pdf
        overwrite:    Replace an existing Volume file only when explicitly true.

    Returns:
        The volume_path confirming where the file was stored.
    """
    local_path = Path(local_path)
    client = WorkspaceClient()

    with open(local_path, "rb") as f:
        client.files.upload(volume_path, f, overwrite=overwrite)

    print(f"Uploaded '{local_path.name}' → {volume_path}")
    return volume_path
