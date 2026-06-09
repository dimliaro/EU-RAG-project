from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DocumentMetadata:
    source: str
    title: str
    url: str
    document_type: str = ""
    publication_date: str = ""
    institution: str = ""
    identifier: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveredDocument:
    metadata: DocumentMetadata
    download_url: str


@dataclass(frozen=True)
class DownloadedDocument:
    discovered: DiscoveredDocument
    local_path: Path
    checksum: str
    content_type: str = ""


@dataclass(frozen=True)
class IngestionResult:
    discovered_count: int
    new_count: int
    skipped_count: int
    documents: list[DiscoveredDocument]


@dataclass(frozen=True)
class CelexIngestionResult:
    celex_id: str
    title: str
    local_path: Path
    volume_path: str
    source_url: str
    pdf_url: str
