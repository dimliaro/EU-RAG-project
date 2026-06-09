import csv

from databricks.sdk import WorkspaceClient


INDEX_NAME = "accenture2026dbcks.team6.team6_panos_index"


def evaluate():

    client = WorkspaceClient()

    total = 0
    correct = 0

    with open("data/evaluation_questions.csv", newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            question = row["question"]
            expected = row["expected_document"]

            results = client.vector_search_indexes.query_index(
                index_name=INDEX_NAME,
                columns=["source_file"],
                query_text=question,
                num_results=1,
            )

            retrieved = results.result.data_array[0][0]

            is_correct = retrieved == expected

            total += 1

            if is_correct:
                correct += 1

            print(
                f"Q: {question}\n"
                f"Expected: {expected}\n"
                f"Retrieved: {retrieved}\n"
                f"{'✓ CORRECT' if is_correct else '✗ WRONG'}\n"
            )

    accuracy = correct / total * 100

    print("=" * 50)
    print(f"Total Questions: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("=" * 50)


if __name__ == "__main__":
    evaluate()