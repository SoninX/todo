import os
from fastapi import HTTPException
from azure.storage.blob import BlobServiceClient

AZURE_CONN_STR = os.getenv("AZURE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "todo-files")

def get_blob_service_client():
    
    if not AZURE_CONN_STR:
        raise HTTPException(status_code=500, detail="Azure Connection String not set")
    return BlobServiceClient.from_connection_string(AZURE_CONN_STR)