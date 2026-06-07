from day_09.all_type_chunker import chunk_file
from databricks.connect import DatabricksSession
import pandas as pd

chunks = chunk_file(
    "/Volumes/accenture2026dbcks/default/data/32016R0679_EN.pdf",
    document_id="32016R0679",
)
print(f"Created {len(chunks)} chunks")

df = pd.DataFrame(chunks)
spark = DatabricksSession.builder.serverless(True).getOrCreate()
spark_df = spark.createDataFrame(df)

(
    spark_df.write
    .format("delta")
    .mode("append")
    .saveAsTable("accenture2026dbcks.team6.eu_law_chunks")
)