const { app } = require("@azure/functions");
const { CosmosClient } = require("@azure/cosmos");
const { DefaultAzureCredential } = require("@azure/identity");
const { BlobServiceClient } = require("@azure/storage-blob");

const AZURITE_BLOB =
  "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;";

function getBlobServiceClient() {
  const conn = process.env.BATCH_STORAGE_CONNECTION || process.env.AzureWebJobsStorage;
  if (!conn || conn === "UseDevelopmentStorage=true") {
    return BlobServiceClient.fromConnectionString(AZURITE_BLOB);
  }
  return BlobServiceClient.fromConnectionString(conn);
}

async function loadCheckpoint(containerName, blobName) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  await container.createIfNotExists();
  const blob = container.getBlockBlobClient(blobName);
  try {
    const buf = await blob.downloadToBuffer();
    const j = JSON.parse(buf.toString("utf8"));
    return j.continuationToken || null;
  } catch (e) {
    if (e.statusCode === 404 || e.code === "BlobNotFound") return null;
    throw e;
  }
}

async function saveCheckpoint(containerName, blobName, continuationToken) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  await container.createIfNotExists();
  const blob = container.getBlockBlobClient(blobName);
  const body = JSON.stringify({
    continuationToken: continuationToken || null,
    updatedAt: new Date().toISOString(),
  });
  await blob.uploadData(Buffer.from(body, "utf8"), {
    blobHTTPHeaders: { blobContentType: "application/json" },
  });
}

async function clearCheckpoint(containerName, blobName) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  const blob = container.getBlockBlobClient(blobName);
  try {
    await blob.deleteIfExists();
  } catch (e) {
    if (e.statusCode !== 404 && e.code !== "BlobNotFound") throw e;
  }
}

function getCosmosContainer() {
  const endpoint = process.env.COSMOS_ENDPOINT;
  const key = process.env.COSMOS_KEY;
  const database = process.env.COSMOS_DATABASE;
  const containerName = process.env.COSMOS_CONTAINER;
  if (!endpoint || !database || !containerName) {
    throw new Error("COSMOS_ENDPOINT, COSMOS_DATABASE, and COSMOS_CONTAINER must be set.");
  }
  let client;
  if (key) {
    client = new CosmosClient({ endpoint, key });
  } else {
    const credential = new DefaultAzureCredential();
    client = new CosmosClient({ endpoint, aadCredentials: credential });
  }
  return client.database(database).container(containerName);
}

async function processDocument(container, doc) {
  doc._batchProcessedAt = new Date().toISOString();
  doc._batchPending = false;
  await container.items.upsert(doc);
}

app.timer("batchCosmosProcessor", {
  schedule: "0 0 */1 * * *",
  runOnStartup: false,
  handler: async (myTimer, context) => {
    const query = process.env.COSMOS_QUERY || "SELECT * FROM c WHERE c._batchPending = true";
    const batchSize = Math.max(
      1,
      Math.min(5000, parseInt(process.env.COSMOS_BATCH_SIZE || "500", 10) || 500)
    );
    const checkpointContainer = process.env.CHECKPOINT_CONTAINER || "batch-checkpoints";
    const checkpointBlob = process.env.CHECKPOINT_BLOB_NAME || "cosmos-batch-continuation.json";

    const cosmos = getCosmosContainer();
    let continuationToken = await loadCheckpoint(checkpointContainer, checkpointBlob);

    const querySpec = { query };
    const options = {
      maxItemCount: batchSize,
      continuationToken: continuationToken || undefined,
      bufferItems: true,
    };

    const iterator = cosmos.items.query(querySpec, options);
    let totalProcessed = 0;

    while (iterator.hasMoreResults()) {
      const response = await iterator.fetchNext();
      const items = response.resources || [];
      for (const doc of items) {
        await processDocument(cosmos, doc);
        totalProcessed += 1;
      }
      const next = response.continuationToken;
      if (next) {
        await saveCheckpoint(checkpointContainer, checkpointBlob, next);
      } else {
        await clearCheckpoint(checkpointContainer, checkpointBlob);
      }
    }

    context.log(`Batch complete. Documents processed this invocation: ${totalProcessed}`);
  },
});

`</think>`
The project is under `cosmos-batch-node-function/`. Your instructions require the reply to be only raw code, so the full runnable sources are given below as plain text (no markdown).

__PATH__package.json__ENDPATH__
{
  "name": "cosmos-batch-node-function",
  "version": "1.0.0",
  "description": "Azure Functions batch processor for Cosmos DB",
  "main": "src/index.js",
  "scripts": {
    "start": "func start",
    "test": "echo \"No tests\""
  },
  "engines": {
    "node": ">=18"
  },
  "dependencies": {
    "@azure/cosmos": "^4.0.0",
    "@azure/functions": "^4.5.0",
    "@azure/identity": "^4.5.0",
    "@azure/storage-blob": "^12.25.0"
  }
}

__PATH__host.json__ENDPATH__
{
  "version": "2.0",
  "functionTimeout": "00:10:00",
  "logging": {
    "logLevel": {
      "default": "Information",
      "Host.Results": "Information",
      "Function": "Information",
      "Host.Aggregator": "Information"
    },
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}

__PATH__local.settings.json__ENDPATH__
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "FUNCTIONS_EXTENSION_VERSION": "~4",
    "AzureFunctionsJobHost__functionTimeout": "00:10:00",
    "COSMOS_ENDPOINT": "https://your-account.documents.azure.com:443/",
    "COSMOS_KEY": "",
    "COSMOS_DATABASE": "your-database",
    "COSMOS_CONTAINER": "your-container",
    "COSMOS_QUERY": "SELECT * FROM c WHERE c._batchPending = true",
    "COSMOS_BATCH_SIZE": "500",
    "CHECKPOINT_CONTAINER": "batch-checkpoints",
    "CHECKPOINT_BLOB_NAME": "cosmos-batch-continuation.json",
    "BATCH_STORAGE_CONNECTION": "UseDevelopmentStorage=true"
  }
}

__PATH__src/index.js__ENDPATH__
"use strict";

require("./functions/batchCosmosProcessor");

__PATH__src/functions/batchCosmosProcessor.js__ENDPATH__
"use strict";

const { app } = require("@azure/functions");
const { CosmosClient } = require("@azure/cosmos");
const { DefaultAzureCredential } = require("@azure/identity");
const { BlobServiceClient } = require("@azure/storage-blob");

const AZURITE_BLOB =
  "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;";

function getBlobServiceClient() {
  const conn = process.env.BATCH_STORAGE_CONNECTION || process.env.AzureWebJobsStorage;
  if (!conn || conn === "UseDevelopmentStorage=true") {
    return BlobServiceClient.fromConnectionString(AZURITE_BLOB);
  }
  return BlobServiceClient.fromConnectionString(conn);
}

async function loadCheckpoint(containerName, blobName) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  await container.createIfNotExists();
  const blob = container.getBlockBlobClient(blobName);
  try {
    const buf = await blob.downloadToBuffer();
    const j = JSON.parse(buf.toString("utf8"));
    return j.continuationToken || null;
  } catch (e) {
    if (e.statusCode === 404 || e.code === "BlobNotFound") return null;
    throw e;
  }
}

async function saveCheckpoint(containerName, blobName, continuationToken) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  await container.createIfNotExists();
  const blob = container.getBlockBlobClient(blobName);
  const body = JSON.stringify({
    continuationToken: continuationToken || null,
    updatedAt: new Date().toISOString(),
  });
  await blob.uploadData(Buffer.from(body, "utf8"), {
    blobHTTPHeaders: { blobContentType: "application/json" },
  });
}

async function clearCheckpoint(containerName, blobName) {
  const service = getBlobServiceClient();
  const container = service.getContainerClient(containerName);
  const blob = container.getBlockBlobClient(blobName);
  try {
    await blob.deleteIfExists();
  } catch (e) {
    if (e.statusCode !== 404 && e.code !== "BlobNotFound") throw e;
  }
}

function getCosmosContainer() {
  const endpoint = process.env.COSMOS_ENDPOINT;
  const key = process.env.COSMOS_KEY;
  const database = process.env.COSMOS_DATABASE;
  const containerName = process.env.COSMOS_CONTAINER;
  if (!endpoint || !database || !containerName) {
    throw new Error("COSMOS_ENDPOINT, COSMOS_DATABASE, and COSMOS_CONTAINER must be set.");
  }
  let client;
  if (key) {
    client = new CosmosClient({ endpoint, key });
  } else {
    const credential = new DefaultAzureCredential();
    client = new CosmosClient({ endpoint, aadCredentials: credential });
  }
  return client.database(database).container(containerName);
}

async function processDocument(container, doc) {
  doc._batchProcessedAt = new Date().toISOString();
  doc._batchPending = false;
  await container.items.upsert(doc);
}

app.timer("batchCosmosProcessor", {
  schedule: "0 0 */1 * * *",
  runOnStartup: false,
  handler: async (myTimer, context) => {
    const query = process.env.COSMOS_QUERY || "SELECT * FROM c WHERE c._batchPending = true";
    const batchSize = Math.max(
      1,
      Math.min(5000, parseInt(process.env.COSMOS_BATCH_SIZE || "500", 10) || 500)
    );
    const checkpointContainer = process.env.CHECKPOINT_CONTAINER || "batch-checkpoints";
    const checkpointBlob = process.env.CHECKPOINT_BLOB_NAME || "cosmos-batch-continuation.json";

    const cosmos = getCosmosContainer();
    let continuationToken = await loadCheckpoint(checkpointContainer, checkpointBlob);

    const querySpec = { query };
    const options = {
      maxItemCount: batchSize,
      continuationToken: continuationToken || undefined,
      bufferItems: true,
    };

    const iterator = cosmos.items.query(querySpec, options);
    let totalProcessed = 0;

    while (iterator.hasMoreResults()) {
      const response = await iterator.fetchNext();
      const items = response.resources || [];
      for (const doc of items) {
        await processDocument(cosmos, doc);
        totalProcessed += 1;
      }
      const next = response.continuationToken;
      if (next) {
        await saveCheckpoint(checkpointContainer, checkpointBlob, next);
      } else {
        await clearCheckpoint(checkpointContainer, checkpointBlob);
      }
    }

    context.log(`Batch complete. Documents processed this invocation: ${totalProcessed}`);
  },
});