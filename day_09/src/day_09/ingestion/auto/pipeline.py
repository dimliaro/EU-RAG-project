from pathlib import Path

from day_09.ingestion.auto.models import CelexIngestionResult, DiscoveredDocument, IngestionResult
from day_09.ingestion.auto.registry import get_source
from day_09.ingestion.auto.sources.eurlex import EurLexSource
from day_09.ingestion.auto.storage.manifest_store import ManifestStore
from day_09.ingestion.auto.storage.volume_writer import VolumeWriter


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

    def ingest_celex_pdf(
        self,
        celex_id: str,
        target_volume_dir: str,
        overwrite: bool = False,
    ) -> CelexIngestionResult:
        source = EurLexSource()
        discovered = source.discover_celex([celex_id], limit=1)
        if not discovered:
            raise ValueError(f"No EUR-Lex document discovered for CELEX ID '{celex_id}'.")

        document = discovered[0]
        downloaded = source.download_celex_pdf(document.metadata.identifier)

        writer = VolumeWriter(target_volume_dir=target_volume_dir)
        volume_path = writer.write_file(
            local_path=downloaded.local_path,
            overwrite=overwrite,
        )

        self.manifest.record_discovered(document)
        self.manifest.save()

        return CelexIngestionResult(
            celex_id=document.metadata.identifier,
            title=document.metadata.title,
            local_path=downloaded.local_path,
            volume_path=volume_path,
            source_url=document.metadata.url,
            pdf_url=document.metadata.extra["pdf_url"],
        )
