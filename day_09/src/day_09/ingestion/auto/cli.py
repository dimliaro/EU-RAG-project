import argparse

from day_09.ingestion.auto.pipeline import AutoIngestionPipeline
from day_09.ingestion.auto.registry import available_sources
from day_09.ingestion.auto.sources.eurlex import EurLexSource
from day_09.ingestion.auto.storage.volume_writer import VolumeWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover official EU regulatory documents.")
    parser.add_argument("--source", default="eurlex", choices=available_sources())
    parser.add_argument("--query")
    parser.add_argument("--celex", nargs="+")
    parser.add_argument("--local-file")
    parser.add_argument("--volume-dir")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--manifest", default="data/auto_ingestion_manifest.json")
    args = parser.parse_args()

    if args.local_file:
        if not args.volume_dir:
            parser.error("--volume-dir is required when --local-file is provided.")

        writer = VolumeWriter(target_volume_dir=args.volume_dir)
        volume_path = writer.write_file(
            local_path=args.local_file,
            overwrite=args.overwrite,
        )
        print(f"Uploaded: {args.local_file}")
        print(f"Volume path: {volume_path}")
        return

    if not args.query and not args.celex:
        parser.error("Provide --query, --celex, or --local-file.")

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
