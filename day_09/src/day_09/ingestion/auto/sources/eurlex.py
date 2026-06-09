from urllib.parse import urlencode

from day_09.ingestion.auto.models import DiscoveredDocument, DocumentMetadata
from day_09.ingestion.auto.sources.base import DocumentSource


class EurLexSource(DocumentSource):
    """EUR-Lex discovery skeleton.

    This first real iteration does not scrape search results yet. It returns a
    discovered search descriptor containing the source, original query, and the
    generated EUR-Lex search URL.
    """

    name = "eurlex"
    base_search_url = "https://eur-lex.europa.eu/search.html"

    def build_search_url(self, query: str) -> str:
        params = {
            "scope": "EURLEX",
            "text": query,
        }
        return f"{self.base_search_url}?{urlencode(params)}"

    def discover(self, query: str, limit: int = 10) -> list[DiscoveredDocument]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        search_url = self.build_search_url(normalized_query)
        metadata = DocumentMetadata(
            source=self.name,
            title=f"EUR-Lex search: {normalized_query}",
            url=search_url,
            document_type="search",
            institution="EUR-Lex",
            identifier=f"eurlex-search:{normalized_query.lower()}",
            extra={
                "query": normalized_query,
                "search_url": search_url,
            },
        )

        return [
            DiscoveredDocument(
                metadata=metadata,
                download_url=search_url,
            )
        ][:limit]
