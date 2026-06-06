"""
reads a pdf file from databricks volume, extracts the text and prints the first 1000 characters of the first page
file: ex5.py    
"""


from io import BytesIO
from pypdf import PdfReader
from databricks.sdk import WorkspaceClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)



def get_pages(pdf_path: str)-> list[dict]:
    logging.info(f"\n------------Extracting pages from: {pdf_path}------------\n")
    w = WorkspaceClient()

    

    pdf_bytes = (
        w.files.download(pdf_path)
        .contents
        .read()
    )

    reader = PdfReader(BytesIO(pdf_bytes))

    pages = []

    for page_num, page in enumerate(reader.pages, start=1):

        page_text = page.extract_text() or ""

        pages.append(
            {
                "page_number": page_num,
                "text": page_text
            }
        )

    logging.info(f"Pages extracted: {len(pages)}")
    logging.info(pages[0]["text"][:1000])   

    return pages

if __name__ == "__main__":
    get_pages("/Volumes/accenture2026dbcks/default/data/32016R0679_EN.pdf")