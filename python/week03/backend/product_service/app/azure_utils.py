# app/azure_utils.py

import os
from azure.storage.blob import BlobServiceClient
from uuid import uuid4
from fastapi import UploadFile

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "product-images")

def upload_to_azure_blob(file: UploadFile) -> str:
    """
    Upload a file to Azure Blob Storage and return the blob URL.
    """
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise Exception("Azure Blob Storage connection string not set")
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
    try:
        container_client.create_container()
    except Exception:
        pass  # Container might already exist
    file_ext = file.filename.split(".")[-1]
    blob_name = f"{uuid4()}.{file_ext}"
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(file.file, overwrite=True)
    return blob_client.url
