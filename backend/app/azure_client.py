import os
from fastapi import HTTPException
from azure.storage.blob import BlobServiceClient

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from openai import AzureOpenAI

AZURE_CONN_STR = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "todo-files")

DOC_INT_ENDPOINT = os.getenv("AZURE_DOC_INT_ENDPOINT")
DOC_INT_KEY = os.getenv("AZURE_DOC_INT_KEY")

AZURE_OPENAI_ENDPOINT=os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_INFERENCE_CREDENTIAL=os.getenv("AZURE_INFERENCE_CREDENTIAL")
AZURE_OPENAI_DEPLOYMENT_NAME=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

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

def get_doc_classified_client():
    if not AZURE_OPENAI_ENDPOINT or not AZURE_INFERENCE_CREDENTIAL:
        raise ValueError("Azure OpenAI Endpoint or Key not set")
    
    client = AzureOpenAI(
        azure_endpoint = AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_INFERENCE_CREDENTIAL,  
        api_version="2024-12-01-preview",
    )
    return client