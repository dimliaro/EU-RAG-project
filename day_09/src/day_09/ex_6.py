"""
file: ex6.py

Split into Chunks
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from day_09.ex_5 import get_pages


pages = get_pages("/Volumes/accenture2026dbcks/default/data/32016R0679_EN.pdf")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = []

for page in pages:

    page_chunks = splitter.split_text(page["text"])

    for chunk_num, chunk in enumerate(page_chunks):

        chunks.append(
            {
                "document_id": "32016R0679",
                "page_number": page["page_number"],
                "chunk_id": chunk_num,
                "chunk_text": chunk,
            }
        )

print(f"Created {len(chunks)} chunks")

catalog = "accenture2026dbcks"
schema = "team6"
table = "chunks_015"

# save chunks to databricks table
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# save chucks to table using dataframe
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
        "accenture2026dbcks.team6.eu_law_chunks"
    )
)
