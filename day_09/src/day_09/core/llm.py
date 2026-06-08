"""
Azure OpenAI chat LLM wrapper via LangChain.

Environment variables required:
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_API_VERSION
    AZURE_OPENAI_DEPLOYMENT_NAME
"""
import os

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv

load_dotenv()


class AzureOpenAIChatLLM:
    """
    Azure OpenAI implementation using LangChain.

    Later, replace with Databricks Foundation Models or another deployment.
    """

    def __init__(self):
        self.client = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            temperature=0,
        )

    def generate(self, question: str, context: str) -> str:
        prompt = f"""Use only the provided context to answer the question.

If the answer is not present in the context, say:
"The document does not contain enough information."

Question:
{question}

Context:
{context}
"""

        response = self.client.invoke(
            [
                SystemMessage(content=(
                    "You answer only from the retrieved document context.\n\n"
                    "The context may contain passages labelled [ARTICLE N] or [RECITAL N].\n"
                    "Treat content labelled [ARTICLE ...] as the binding legal rule.\n"
                    "Treat content labelled [RECITAL ...] as explanatory background only.\n"
                    "When both are present, cite the Article as the rule and the Recital "
                    "as supporting context, and make that distinction explicit in your answer."
                )),
                HumanMessage(content=prompt),
            ]
        )

        return response.content
