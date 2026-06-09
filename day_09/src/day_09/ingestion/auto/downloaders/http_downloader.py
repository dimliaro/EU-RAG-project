from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from day_09.ingestion.auto.models import DiscoveredDocument, DownloadedDocument


class HTTPDownloader:
    def __init__(self, user_agent: str = "EU-RAG-auto-ingestion/0.1"):
        self.user_agent = user_agent

    def download(
        self,
        document: DiscoveredDocument,
        destination: Path | str,
        timeout: int = 30,
        expected_content_type: str | None = None,
    ) -> DownloadedDocument:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        request = Request(
            document.download_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": expected_content_type or "*/*",
            },
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "")
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Failed to download {document.download_url}: {exc}") from exc

        if not content:
            raise RuntimeError(f"Downloaded empty response from {document.download_url}")

        if expected_content_type and expected_content_type not in content_type:
            raise RuntimeError(
                f"Expected {expected_content_type} from {document.download_url}, "
                f"got {content_type or 'unknown content type'}"
            )

        destination_path.write_bytes(content)
        checksum = sha256(content).hexdigest()

        return DownloadedDocument(
            discovered=document,
            local_path=destination_path,
            checksum=checksum,
            content_type=content_type,
        )
