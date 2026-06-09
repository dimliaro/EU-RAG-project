from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, ResourceDoesNotExist


class VolumeWriter:
    """Write locally downloaded auto-ingestion files to a Databricks Volume."""

    def __init__(
        self,
        target_volume_dir: str,
        client: WorkspaceClient | None = None,
    ):
        self.target_volume_dir = target_volume_dir.rstrip("/")
        self.client = client or WorkspaceClient()

    def write_file(
        self,
        local_path: str | Path,
        overwrite: bool = False,
    ) -> str:
        source_path = Path(local_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Local file does not exist: {source_path}")
        if not source_path.is_file():
            raise ValueError(f"Local path is not a file: {source_path}")

        volume_path = f"{self.target_volume_dir}/{source_path.name}"

        self._ensure_target_dir()
        if not overwrite and self._exists(volume_path):
            raise FileExistsError(
                f"Volume file already exists: {volume_path}. "
                "Pass overwrite=True to replace it."
            )

        with source_path.open("rb") as file_handle:
            self.client.files.upload(
                volume_path,
                file_handle,
                overwrite=overwrite,
            )

        return volume_path

    def _ensure_target_dir(self) -> None:
        self.client.files.create_directory(self.target_volume_dir)

    def _exists(self, volume_path: str) -> bool:
        try:
            self.client.files.get_metadata(volume_path)
        except (NotFound, ResourceDoesNotExist):
            return False
        return True
