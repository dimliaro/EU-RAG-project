from pathlib import Path

from day_09.ingestion.auto.models import DiscoveredDocument, IngestionResult
from day_09.ingestion.auto.registry import get_source
from day_09.ingestion.auto.storage.manifest_store import ManifestStore


class AutoIngestionPipeline:
    """Coordinates source discovery and local manifest tracking."""

    def __init__(self, manifest_path: Path | str = "data/auto_ingestion_manifest.json"):
        self.manifest = ManifestStore(manifest_path)

    def discover(
        self,
        source_name: str,
        query: str,
        limit: int = 10,
    ) -> IngestionResult:
        source = get_source(source_name)
        documents = source.discover(query=query, limit=limit)

        new_documents: list[DiscoveredDocument] = []
        skipped_count = 0

        for document in documents:
            key = document.metadata.identifier or document.metadata.url
            if self.manifest.contains(key):
                skipped_count += 1
                continue
            new_documents.append(document)
            self.manifest.record_discovered(document)

        self.manifest.save()

        return IngestionResult(
            discovered_count=len(documents),
            new_count=len(new_documents),
            skipped_count=skipped_count,
            documents=new_documents,
        )

