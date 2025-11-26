import os
from fastapi import HTTPException
from azure.storage.blob import BlobServiceClient

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

AZURE_CONN_STR = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "todo-files")

DOC_INT_ENDPOINT = os.getenv("AZURE_DOC_INT_ENDPOINT")
DOC_INT_KEY = os.getenv("AZURE_DOC_INT_KEY")

def get_blob_service_client():
    
    if not AZURE_CONN_STR:
        raise HTTPException(status_code=500, detail="Azure Connection String not set")
    return BlobServiceClient.from_connection_string(AZURE_CONN_STR)

def get_document_analysis_client():

    if not DOC_INT_ENDPOINT or not DOC_INT_KEY:
        raise ValueError("Azure Document Intelligence Endpoint or Key not set")
    
    return DocumentAnalysisClient(
        endpoint=DOC_INT_ENDPOINT, 
        credential=AzureKeyCredential(DOC_INT_KEY)
    )