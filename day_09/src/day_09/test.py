
"""
testing Azure OpenAI integration with LangChain. Make sure to set up your .env file with the following variables:
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
"""

import os
from dotenv import load_dotenv
# 1. Correct import for LangChain's Azure OpenAI integration
from langchain_openai import AzureChatOpenAI

# Load environment variables from the .env file
load_dotenv()

# 2. Initialize the Azure model using your environment variables
azure_model = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    temperature=0,
)

# 3. Invoke the model
prompt = input("Give question:")
response = azure_model.invoke(prompt)

# 4. Extract the text content
print(response.content)

