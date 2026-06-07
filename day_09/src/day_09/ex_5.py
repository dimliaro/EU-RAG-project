"""
reads a pdf file from databricks volume, extracts the text and prints the first 1000 characters of the first page
file: ex5.py    
"""

import pymupdf
from databricks.sdk import WorkspaceClient
import logging
#workspace client connects with databricks workspace and allows us to interact with files in the databricks volume
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def get_pages(pdf_path: str) -> list[dict]:
    logging.info(f"\n------------Extracting pages from: {pdf_path}------------\n")
    w = WorkspaceClient()

    pdf_bytes = (
        w.files.download(pdf_path)
        .contents
        .read()
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    pages = []

    for page_num, page in enumerate(doc, start=1):

        page_text = page.get_text() or ""

        pages.append(
            {
                "page_number": page_num,
                "text": page_text
            }
        )

    doc.close()

    logging.info(f"Pages extracted: {len(pages)}")
    logging.info(pages[0]["text"][:1000])

    return pages


if __name__ == "__main__":
    get_pages("/Volumes/accenture2026dbcks/default/data/32016R0679_EN.pdf")
