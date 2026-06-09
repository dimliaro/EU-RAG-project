import argparse

from day_09.ingestion.auto.pipeline import AutoIngestionPipeline
from day_09.ingestion.auto.registry import available_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover official EU regulatory documents.")
    parser.add_argument("--source", default="eurlex", choices=available_sources())
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--manifest", default="data/auto_ingestion_manifest.json")
    args = parser.parse_args()

    pipeline = AutoIngestionPipeline(manifest_path=args.manifest)
    result = pipeline.discover(
        source_name=args.source,
        query=args.query,
        limit=args.limit,
    )

    print(f"Discovered: {result.discovered_count}")
    print(f"New: {result.new_count}")
    print(f"Skipped: {result.skipped_count}")

    for document in result.documents:
        print(f"- {document.metadata.title} [{document.metadata.url}]")


if __name__ == "__main__":
    main()

