// app/azure.js
const { BlobServiceClient } = require('@azure/storage-blob');
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config();

const AZURE_CONNECTION_STRING = process.env.AZURE_STORAGE_CONNECTION_STRING;
const AZURE_CONTAINER_NAME = process.env.AZURE_CONTAINER_NAME || "product-images";

async function uploadToAzure(fileBuffer, originalName, mimetype) {
  if (!AZURE_CONNECTION_STRING) throw new Error('Azure connection string not set');
  const blobServiceClient = BlobServiceClient.fromConnectionString(AZURE_CONNECTION_STRING);
  const containerClient = blobServiceClient.getContainerClient(AZURE_CONTAINER_NAME);
  try { await containerClient.createIfNotExists(); } catch {}
  const ext = originalName.split('.').pop();
  const blobName = `${uuidv4()}.${ext}`;
  const blockBlobClient = containerClient.getBlockBlobClient(blobName);
  await blockBlobClient.uploadData(fileBuffer, {
    blobHTTPHeaders: { blobContentType: mimetype }
  });
  return blockBlobClient.url;
}

module.exports = { uploadToAzure };
