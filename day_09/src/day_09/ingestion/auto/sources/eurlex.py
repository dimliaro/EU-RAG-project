from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from day_09.ingestion.auto.downloaders.http_downloader import HTTPDownloader
from day_09.ingestion.auto.models import DiscoveredDocument, DocumentMetadata
from day_09.ingestion.auto.models import DownloadedDocument
from day_09.ingestion.auto.sources.base import DocumentSource


class _ResultLinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if href and self._is_result_href(href):
            self._active_href = urljoin(self.base_url, href)
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._active_href:
            return

        title = " ".join(" ".join(self._active_text).split())
        self.links.append((self._active_href, title))
        self._active_href = None
        self._active_text = []

    @staticmethod
    def _is_result_href(href: str) -> bool:
        return "/legal-content/" in href and "uri=" in href


class EurLexSource(DocumentSource):
    """EUR-Lex search-result discovery.

    This fetches the EUR-Lex search results page and extracts legal-content
    result URLs. It does not download PDFs or parse document pages yet.
    """

    name = "eurlex"
    base_search_url = "https://eur-lex.europa.eu/search.html"
    base_txt_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/"
    base_pdf_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/"
    user_agent = "EU-RAG-auto-ingestion/0.1"
    known_celex_titles = {
        "32016R0679": "GDPR",
        "32022R2554": "DORA",
        "32024R1689": "AI Act",
        "32014L0065": "MiFID II",
        "32013L0036": "CRD IV",
    }

    def build_search_url(self, query: str) -> str:
        params = {
            "lang": "en",
            "scope": "EURLEX",
            "text": query,
            "type": "quick",
        }
        return f"{self.base_search_url}?{urlencode(params)}"

    def build_document_url(self, celex_id: str) -> str:
        return self.build_txt_url(celex_id)

    def build_txt_url(self, celex_id: str) -> str:
        return f"{self.base_txt_url}?{urlencode({'uri': f'CELEX:{celex_id}'})}"

    def build_pdf_url(self, celex_id: str) -> str:
        return f"{self.base_pdf_url}?{urlencode({'uri': f'CELEX:{celex_id}'})}"

    def discover_celex(self, celex_ids: list[str], limit: int | None = None) -> list[DiscoveredDocument]:
        documents: list[DiscoveredDocument] = []

        for raw_celex_id in celex_ids:
            celex_id = raw_celex_id.strip().upper()
            if not celex_id:
                continue

            title = self.known_celex_titles.get(celex_id, celex_id)
            txt_url = self.build_txt_url(celex_id)
            pdf_url = self.build_pdf_url(celex_id)
            metadata = DocumentMetadata(
                source=self.name,
                title=title,
                url=txt_url,
                document_type="eurlex-document",
                institution="EUR-Lex",
                identifier=celex_id,
                extra={
                    "celex_id": celex_id,
                    "discovery_method": "celex_direct",
                    "txt_url": txt_url,
                    "pdf_url": pdf_url,
                },
            )

            documents.append(
                DiscoveredDocument(
                    metadata=metadata,
                    download_url=txt_url,
                )
            )

            if limit is not None and len(documents) >= limit:
                break

        return documents

    def download_celex_pdf(
        self,
        celex_id: str,
        download_dir: Path | str | None = None,
    ) -> DownloadedDocument:
        document = self._build_celex_pdf_document(celex_id)
        destination_dir = (
            Path(download_dir)
            if download_dir is not None
            else Path(__file__).resolve().parents[1] / "tmp" / "eurlex"
        )
        destination = destination_dir / f"{document.metadata.identifier}.pdf"

        downloader = HTTPDownloader(user_agent=self.user_agent)
        return downloader.download(
            document=document,
            destination=destination,
            expected_content_type="application/pdf",
        )

    def _build_celex_pdf_document(self, celex_id: str) -> DiscoveredDocument:
        normalized_celex_id = celex_id.strip().upper()
        title = self.known_celex_titles.get(normalized_celex_id, normalized_celex_id)
        txt_url = self.build_txt_url(normalized_celex_id)
        pdf_url = self.build_pdf_url(normalized_celex_id)
        metadata = DocumentMetadata(
            source=self.name,
            title=title,
            url=txt_url,
            document_type="eurlex-pdf",
            institution="EUR-Lex",
            identifier=normalized_celex_id,
            extra={
                "celex_id": normalized_celex_id,
                "discovery_method": "celex_direct",
                "txt_url": txt_url,
                "pdf_url": pdf_url,
            },
        )
        return DiscoveredDocument(
            metadata=metadata,
            download_url=pdf_url,
        )

    def discover(self, query: str, limit: int = 10) -> list[DiscoveredDocument]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        search_url = self.build_search_url(normalized_query)
        html = self._fetch_search_results(search_url)
        result_links = self._extract_result_links(html=html, search_url=search_url)

        documents: list[DiscoveredDocument] = []
        seen: set[str] = set()

        for result_url, title in result_links:
            if result_url in seen:
                continue
            seen.add(result_url)

            identifier = self._identifier_from_url(result_url)
            metadata = DocumentMetadata(
                source=self.name,
                title=title or result_url,
                url=result_url,
                document_type="eurlex-result",
                institution="EUR-Lex",
                identifier=identifier or result_url,
                extra={
                    "query": normalized_query,
                    "search_url": search_url,
                },
            )

            documents.append(
                DiscoveredDocument(
                    metadata=metadata,
                    download_url=result_url,
                )
            )

            if len(documents) >= limit:
                break

        return documents

    def _fetch_search_results(self, search_url: str) -> str:
        request = Request(
            search_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(content_type, errors="replace")

        if "AwsWafIntegration" in html or "challenge-container" in html:
            raise RuntimeError(
                "EUR-Lex returned an automated-access challenge instead of search results."
            )

        return html

    @staticmethod
    def _extract_result_links(html: str, search_url: str) -> list[tuple[str, str]]:
        parser = _ResultLinkParser(base_url=search_url)
        parser.feed(html)
        return parser.links

    @staticmethod
    def _identifier_from_url(result_url: str) -> str:
        parsed = urlparse(result_url)
        query = parse_qs(parsed.query)
        uri_values = query.get("uri", [])
        if not uri_values:
            return ""

        uri = uri_values[0]
        if ":" in uri:
            return uri.rsplit(":", 1)[-1]
        return uri
