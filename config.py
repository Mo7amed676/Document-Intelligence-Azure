from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("ENDPOINT")
key = os.getenv("KEY")

def get_client() -> DocumentIntelligenceClient:
    """
    Create and return an Azure Document Intelligence client.
    """
    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )