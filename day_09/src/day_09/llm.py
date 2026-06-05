"""
file: llm.py
This module defines the AzureOpenAIChatLLM class, which provides functionality to generate responses using
Azure OpenAI's chat models via the LangChain library. The class is designed to be easily replaceable with other LLM implementations in the future, such as Databricks Foundation Models or other Azure OpenAI deployments.

"""
import os

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv
# Load environment variables from the .env file
load_dotenv()

class AzureOpenAIChatLLM:
    """
    Azure OpenAI implementation using LangChain.

    Environment Variables:

    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_API_VERSION
    AZURE_OPENAI_DEPLOYMENT_NAME
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

        prompt = f"""
You are a grounded RAG assistant.

Use only the provided context to answer the question.

If the answer is not present in the context, say:
"The document does not contain enough information."

Question:
{question}

Context:
{context}
"""

        response = self.client.invoke(
            [
                SystemMessage(
                    content="You answer only from the retrieved document context."
                ),
                HumanMessage(content=prompt),
            ]
        )

        return response.content