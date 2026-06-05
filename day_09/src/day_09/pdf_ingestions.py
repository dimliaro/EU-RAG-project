"""
PDF Ingestion Module
This module provides functionality to extract text from PDF files using the PyMuPDF library.
The main function, `extract_pdf_pages`, takes the path to a PDF file and returns a  
list of dictionaries, each containing the source file path, page number, and extracted text for that page.

pdf_ingestion.py

"""

import fitz


def extract_pdf_pages(pdf_path: str)-> list[dict[str, str | int]]:
    """
    Extract text from PDF using PyMuPDF.

    Later in Databricks:
    - pdf_path can become /Volumes/catalog/schema/volume/file.pdf
    - output can be saved into a Delta table
    """

    doc = fitz.open(pdf_path)
    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")

        if text and text.strip():
            pages.append(
                {
                    "source_file": str(pdf_path),
                    "page_number": page_number,
                    "text": text.strip(),
                }
            )

    return pages