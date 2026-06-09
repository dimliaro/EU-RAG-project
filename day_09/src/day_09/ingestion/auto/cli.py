import argparse

from day_09.ingestion.auto.pipeline import AutoIngestionPipeline
from day_09.ingestion.auto.registry import available_sources
from day_09.ingestion.auto.sources.eurlex import EurLexSource


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover official EU regulatory documents.")
    parser.add_argument("--source", default="eurlex", choices=available_sources())
    parser.add_argument("--query")
    parser.add_argument("--celex", nargs="+")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--manifest", default="data/auto_ingestion_manifest.json")
    args = parser.parse_args()

    if not args.query and not args.celex:
        parser.error("Provide either --query or --celex.")

    if args.celex:
        if args.source != "eurlex":
            parser.error("--celex is currently supported only with --source eurlex.")

        source = EurLexSource()
        documents = source.discover_celex(args.celex, limit=args.limit)
        print(f"Discovered: {len(documents)}")

        for document in documents:
            print(f"- {document.metadata.title} [{document.metadata.url}]")
            print(f"  CELEX: {document.metadata.identifier}")
            print(f"  PDF: {document.metadata.extra['pdf_url']}")

        return

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
