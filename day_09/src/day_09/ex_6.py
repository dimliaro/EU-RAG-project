"""
file: ex6.py

Split into Chunks (semantic)
"""
from day_09.ex_5 import get_pages
from day_09.chunking import chunk_text
from day_09.config import CHUNK_SIZE, CHUNK_OVERLAP


pages = get_pages("/Volumes/accenture2026dbcks/team6/volume/pdfs/32022R2554_EN.pdf")

chunks = []

for page in pages:

    page_chunks = chunk_text(page["text"], chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

    for chunk_num, chunk in enumerate(page_chunks):

        chunks.append(
            {
                "document_id": "32022R2554",
                "page_number": page["page_number"],
                "chunk_id": chunk_num,
                "chunk_text": chunk,
            }
        )

print(f"Created {len(chunks)} chunks")

catalog = "accenture2026dbcks"
schema = "team6"
#table = "chunks_015"

# save chunks to databricks table
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# save chunks to table using dataframe
import pandas as pd
df = pd.DataFrame(chunks)

print(df.head())

#Save Chunks to Databricks
from databricks.connect import DatabricksSession

spark = (
    DatabricksSession.builder
    .serverless(True)
    .getOrCreate()
)

spark_df = spark.createDataFrame(df)

(
    spark_df.write
    .format("delta")
    .mode("append")
    .saveAsTable(
        "accenture2026dbcks.team6.eu_law_chunks_fitz4"
    )
)