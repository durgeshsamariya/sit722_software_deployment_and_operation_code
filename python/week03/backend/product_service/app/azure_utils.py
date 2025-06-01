# app/azure_utils.py


"""
Utility functions for interacting with Azure Blob Storage.

This module provides functionality to upload files (e.g., product images)
to an Azure Blob Storage container and retrieve their public URLs.
"""

import os
import logging
from uuid import uuid4
from fastapi import UploadFile

from azure.core.exceptions import ResourceExistsError # Import specific Azure exception
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "product-images")

# Configure logging for this module
logger = logging.getLogger(__name__)
# Basic logging configuration if not already set by main app
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def upload_to_azure_blob(file: UploadFile) -> str:
    """
    Uploads a file to Azure Blob Storage and returns the public URL of the blob.

    This function connects to Azure Blob Storage using the provided connection string
    and container name. It attempts to create the container if it doesn't exist.
    A unique blob name is generated using UUID to prevent collisions.

    Args:
        file (UploadFile): The file object received from FastAPI's UploadFile.

    Returns:
        str: The public URL of the uploaded blob.

    Raises:
        Exception: If the Azure Blob Storage connection string is not set,
                    or if any other error occurs during the upload process.
    """
    
    # Validate that the connection string is set before proceeding.
    if not AZURE_STORAGE_CONNECTION_STRING:
        logger.error("AZURE_STORAGE_CONNECTION_STRING environment variable is not set.")
        raise Exception("Azure Blob Storage connection string not set. "
                        "Please configure AZURE_STORAGE_CONNECTION_STRING.")
    
    try:
        # Create a BlobServiceClient to interact with the Azure Storage account.
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        
        # Get a client for the specific container where images will be stored.
        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

        # Attempt to create the container.
        # If it already exists, a ResourceExistsError will be raised, which we can ignore.
        try:
            container_client.create_container()
            logger.info(f"Azure Blob Storage container '{AZURE_CONTAINER_NAME}' created (or already exists).")
        except ResourceExistsError:
            # This exception is expected if the container already exists, so we can pass.
            logger.debug(f"Azure Blob Storage container '{AZURE_CONTAINER_NAME}' already exists.")
        except Exception as e:
            # Catch any other unexpected errors during container creation.
            logger.error(f"Error creating/accessing Azure Blob Storage container '{AZURE_CONTAINER_NAME}': {e}")
            raise # Re-raise to indicate a critical setup issue
        
        # Generate a unique blob name using UUID to avoid naming conflicts.
        # The original file extension is preserved.
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
        blob_name = f"{uuid4()}.{file_ext}"
        
        # Get a client for the specific blob (file) within the container.
        blob_client = container_client.get_blob_client(blob_name)

        # Upload the file's content.
        # 'overwrite=True' ensures that if a blob with the same name somehow existed, it would be replaced.
        # It's less likely with UUID, but good for robustness.
        blob_client.upload_blob(file.file, overwrite=True)
        logger.info(f"File '{file.filename}' uploaded successfully as '{blob_name}' to Azure Blob Storage.")

        # Return the public URL of the uploaded blob.
        return blob_client.url
    
    except Exception as e:
        # Catch any other exceptions that might occur during the upload process.
        logger.error(f"Failed to upload file to Azure Blob Storage: {e}", exc_info=True)
        raise # Re-raise the exception to be handled by the calling function (e.g., FastAPI endpoint)
