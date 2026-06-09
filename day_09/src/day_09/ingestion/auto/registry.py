from day_09.ingestion.auto.sources.base import DocumentSource
from day_09.ingestion.auto.sources.eurlex import EurLexSource


_SOURCES: dict[str, type[DocumentSource]] = {
    "eurlex": EurLexSource,
}


def available_sources() -> list[str]:
    return sorted(_SOURCES)


def get_source(name: str) -> DocumentSource:
    key = name.lower().strip()
    source_cls = _SOURCES.get(key)
    if source_cls is None:
        supported = ", ".join(available_sources())
        raise ValueError(f"Unsupported source '{name}'. Supported sources: {supported}")
    return source_cls()

