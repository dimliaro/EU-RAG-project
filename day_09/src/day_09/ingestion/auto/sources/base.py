from abc import ABC, abstractmethod

from day_09.ingestion.auto.models import DiscoveredDocument


class DocumentSource(ABC):
    name: str

    @abstractmethod
    def discover(self, query: str, limit: int = 10) -> list[DiscoveredDocument]:
        """Return documents discovered from an official public source."""

