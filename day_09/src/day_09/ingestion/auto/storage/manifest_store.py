import json
from datetime import datetime, timezone
from pathlib import Path

from day_09.ingestion.auto.models import DiscoveredDocument


class ManifestStore:
    """Local JSON manifest used to avoid rediscovering the same document."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.records: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.records = {}
            return
        self.records = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def contains(self, key: str) -> bool:
        return key in self.records

    def record_discovered(self, document: DiscoveredDocument) -> None:
        metadata = document.metadata
        key = metadata.identifier or metadata.url
        self.records[key] = {
            "source": metadata.source,
            "title": metadata.title,
            "url": metadata.url,
            "download_url": document.download_url,
            "document_type": metadata.document_type,
            "publication_date": metadata.publication_date,
            "institution": metadata.institution,
            "identifier": metadata.identifier,
            "extra": metadata.extra,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
