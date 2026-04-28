#!/usr/bin/env bash
set -euo pipefail

APP_DIR="azure-function-batch-processor"

mkdir -p "${APP_DIR}/src/functions"

cat > "${APP_DIR}/package.json" <<'EOF'
{
  "name": "azure-function-batch-processor",
  "version": "1.0.0",
  "private": true,
  "description": "Azure Function app for resilient Cosmos DB batch processing.",
  "main": "src/functions/*.js",
  "scripts": {
    "start": "func start",
    "start:verbose": "func start --verbose"
  },
  "dependencies": {
    "@azure/cosmos": "^4.3.0",
    "@azure/functions": "^4.6.0",
    "@azure/storage-queue": "^12.18.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
EOF

cat > "${APP_DIR}/host.json" <<'EOF'
{
  "version": "2.0",
  "functionTimeout": "00:10:00",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensions": {
    "queues": {
      "batchSize": 1,
      "newBatchThreshold": 0,
      "maxDequeueCount": 5,
      "visibilityTimeout": "00:10:00"
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
EOF

cat > "${APP_DIR}/local.settings.json" <<'EOF'
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "node",
    "COSMOS_DB_CONNECTION_STRING": "AccountEndpoint=https://your-account.documents.azure.com:443/;AccountKey=your-key;",
    "COSMOS_DB_DATABASE_NAME": "appdb",
    "COSMOS_DB_SOURCE_CONTAINER_NAME": "source",
    "COSMOS_DB_JOB_CONTAINER_NAME": "_batchJobs",
    "COSMOS_DB_OUTPUT_CONTAINER_NAME": "processedRecords",
    "BATCH_QUEUE_NAME": "cosmos-batch-jobs",
    "COSMOS_DB_SOURCE_QUERY": "SELECT * FROM c",
    "PROCESSING_PAGE_SIZE": "100",
    "MAX_PARALLEL_WRITES": "10",
    "TIMEOUT_SAFETY_WINDOW_MS": "45000"
  }
}
EOF

cat > "${APP_DIR}/src/functions/batchProcessor.js" <<'EOF'
const { app } = require('@azure/functions');
const { CosmosClient } = require('@azure/cosmos');
const { QueueClient } = require('@azure/storage-queue');
const { createHash, randomUUID } = require('node:crypto');

const JOB_TYPE = 'cosmos-batch-job';
const DEFAULT_SOURCE_QUERY = 'SELECT * FROM c';
const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_MAX_PARALLEL_WRITES = 10;
const DEFAULT_TIMEOUT_SAFETY_WINDOW_MS = 45_000;
const MAX_CONSUMPTION_INVOCATION_MS = 10 * 60 * 1000;

let resourcesPromise;

function getEnv(name, fallback) {
  const value = process.env[name];
  return value === undefined || value === '' ? fallback : value;
}

function getRequiredEnv(name) {
  const value = getEnv(name);
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function parsePositiveInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isNotFoundError(error) {
  return error && (error.code === 404 || error.statusCode === 404);
}

function createOutputId(jobId, sourceId) {
  return createHash('sha256').update(`${jobId}:${sourceId}`).digest('hex');
}

function stripSystemProperties(document) {
  const clean = { ...document };
  delete clean._attachments;
  delete clean._etag;
  delete clean._rid;
  delete clean._self;
  delete clean._ts;
  return clean;
}

function createTransformedRecord(document, jobId) {
  const userFieldNames = Object.keys(document).filter((key) => !key.startsWith('_'));

  return {
    id: createOutputId(jobId, document.id),
    jobId,
    sourceId: document.id,
    processedAt: new Date().toISOString(),
    metadata: {
      fieldCount: userFieldNames.length,
      sourceTimestamp: document._ts ?? null
    },
    document: stripSystemProperties(document)
  };
}

async function getResources() {
  if (!resourcesPromise) {
    resourcesPromise = initializeResources();
  }
  return resourcesPromise;
}

async function initializeResources() {
  const cosmosConnectionString = getRequiredEnv('COSMOS_DB_CONNECTION_STRING');
  const storageConnectionString = getRequiredEnv('AzureWebJobsStorage');
  const databaseName = getRequiredEnv('COSMOS_DB_DATABASE_NAME');
  const sourceContainerName = getRequiredEnv('COSMOS_DB_SOURCE_CONTAINER_NAME');
  const jobContainerName = getEnv('COSMOS_DB_JOB_CONTAINER_NAME', '_batchJobs');
  const outputContainerName = getEnv('COSMOS_DB_OUTPUT_CONTAINER_NAME', 'processedRecords');
  const queueName = getEnv('BATCH_QUEUE_NAME', 'cosmos-batch-jobs');

  const cosmosClient = new CosmosClient(cosmosConnectionString);
  const queueClient = QueueClient.fromConnectionString(storageConnectionString, queueName);

  await queueClient.createIfNotExists();

  const { database } = await cosmosClient.databases.createIfNotExists({ id: databaseName });
  const sourceContainer = database.container(sourceContainerName);
  const jobContainerResponse = await database.containers.createIfNotExists({
    id: jobContainerName,
    partitionKey: { paths: ['/jobType'] }
  });
  const outputContainerResponse = await database.containers.createIfNotExists({
    id: outputContainerName,
    partitionKey: { paths: ['/jobId'] }
  });

  await sourceContainer.read();

  return {
    queueClient,
    sourceContainer,
    jobContainer: jobContainerResponse.container,
    outputContainer: outputContainerResponse.container
  };
}

async function enqueueJob(queueClient, payload) {
  await queueClient.sendMessage(JSON.stringify(payload));
}

async function readJob(jobContainer, jobId) {
  try {
    const response = await jobContainer.item(jobId, JOB_TYPE).read();
    return response.resource ?? null;
  } catch (error) {
    if (isNotFoundError(error)) {
      return null;
    }
    throw error;
  }
}

async function saveJob(jobContainer, job) {
  const normalized = {
    ...job,
    jobType: JOB_TYPE,
    updatedAt: new Date().toISOString()
  };

  await jobContainer.items.upsert(normalized);
  return normalized;
}

async function fetchNextPage(sourceContainer, queryText, continuationToken, pageSize) {
  const iterator = sourceContainer.items.query(queryText, {
    continuationToken: continuationToken || undefined,
    maxItemCount: pageSize
  });

  const response = await iterator.fetchNext();

  return {
    documents: response.resources ?? [],
    continuationToken: response.continuationToken ?? null
  };
}

async function processBatch(outputContainer, documents, jobId, maxParallelWrites) {
  for (let index = 0; index < documents.length; index += maxParallelWrites) {
    const slice = documents.slice(index, index + maxParallelWrites);
    await Promise.all(
      slice.map((document) => outputContainer.items.upsert(createTransformedRecord(document, jobId)))
    );
  }
}

function getProcessingConfig(job) {
  return {
    pageSize: parsePositiveInt(
      String(job.pageSize ?? getEnv('PROCESSING_PAGE_SIZE', DEFAULT_PAGE_SIZE)),
      DEFAULT_PAGE_SIZE
    ),
    maxParallelWrites: parsePositiveInt(
      String(job.maxParallelWrites ?? getEnv('MAX_PARALLEL_WRITES', DEFAULT_MAX_PARALLEL_WRITES)),
      DEFAULT_MAX_PARALLEL_WRITES
    ),
    timeoutSafetyWindowMs: parsePositiveInt(
      String(job.timeoutSafetyWindowMs ?? getEnv('TIMEOUT_SAFETY_WINDOW_MS', DEFAULT_TIMEOUT_SAFETY_WINDOW_MS)),
      DEFAULT_TIMEOUT_SAFETY_WINDOW_MS
    )
  };
}

async function runBatchProcessor(jobId, invocationId) {
  const { sourceContainer, jobContainer, outputContainer, queueClient } = await getResources();
  const existingJob = await readJob(jobContainer, jobId);

  if (!existingJob) {
    throw new Error(`Batch job ${jobId} does not exist.`);
  }

  if (existingJob.status === 'completed') {
    return existingJob;
  }

  const now = new Date().toISOString();
  const queryText = existingJob.queryText || getEnv('COSMOS_DB_SOURCE_QUERY', DEFAULT_SOURCE_QUERY);
  const config = getProcessingConfig(existingJob);
  const deadline = Date.now() + (MAX_CONSUMPTION_INVOCATION_MS - config.timeoutSafetyWindowMs);

  let job = await saveJob(jobContainer, {
    ...existingJob,
    status: 'running',
    startedAt: existingJob.startedAt || now,
    lastHeartbeatAt: now,
    lastInvocationId: invocationId,
    error: null
  });

  let continuationToken = job.continuationToken || null;
  let processedCount = job.processedCount || 0;
  let batchCount = job.batchCount || 0;

  while (Date.now() < deadline) {
    const page = await fetchNextPage(sourceContainer, queryText, continuationToken, config.pageSize);

    if (page.documents.length === 0 && !page.continuationToken) {
      job = await saveJob(jobContainer, {
        ...job,
        status: 'completed',
        continuationToken: null,
        processedCount,
        batchCount,
        completedAt: new Date().toISOString(),
        lastHeartbeatAt: new Date().toISOString()
      });
      return job;
    }

    if (page.documents.length > 0) {
      await processBatch(outputContainer, page.documents, job.id, config.maxParallelWrites);
      processedCount += page.documents.length;
      batchCount += 1;
    }

    continuationToken = page.continuationToken;

    job = await saveJob(jobContainer, {
      ...job,
      status: continuationToken ? 'running' : 'completed',
      continuationToken,
      processedCount,
      batchCount,
      lastBatchSize: page.documents.length,
      lastHeartbeatAt: new Date().toISOString(),
      completedAt: continuationToken ? null : new Date().toISOString()
    });

    if (!continuationToken) {
      return job;
    }
  }

  job = await saveJob(jobContainer, {
    ...job,
    status: 'queued',
    continuationToken,
    processedCount,
    batchCount,
    lastHeartbeatAt: new Date().toISOString()
  });

  await enqueueJob(queueClient, { jobId: job.id, reason: 'continue' });

  return job;
}

app.http('startBatchProcessing', {
  methods: ['POST'],
  authLevel: 'function',
  route: 'batch/start',
  handler: async (request) => {
    const payload = await request.json().catch(() => ({}));
    const { jobContainer, queueClient } = await getResources();
    const createdAt = new Date().toISOString();
    const jobId = payload.jobId || randomUUID();

    const job = {
      id: jobId,
      jobType: JOB_TYPE,
      status: 'queued',
      createdAt,
      startedAt: null,
      completedAt: null,
      updatedAt: createdAt,
      continuationToken: payload.continuationToken || null,
      processedCount: 0,
      batchCount: 0,
      lastBatchSize: 0,
      queryText: payload.queryText || getEnv('COSMOS_DB_SOURCE_QUERY', DEFAULT_SOURCE_QUERY),
      pageSize: parsePositiveInt(
        String(payload.pageSize ?? getEnv('PROCESSING_PAGE_SIZE', DEFAULT_PAGE_SIZE)),
        DEFAULT_PAGE_SIZE
      ),
      maxParallelWrites: parsePositiveInt(
        String(payload.maxParallelWrites ?? getEnv('MAX_PARALLEL_WRITES', DEFAULT_MAX_PARALLEL_WRITES)),
        DEFAULT_MAX_PARALLEL_WRITES
      ),
      timeoutSafetyWindowMs: parsePositiveInt(
        String(payload.timeoutSafetyWindowMs ?? getEnv('TIMEOUT_SAFETY_WINDOW_MS', DEFAULT_TIMEOUT_SAFETY_WINDOW_MS)),
        DEFAULT_TIMEOUT_SAFETY_WINDOW_MS
      ),
      sourceContainerName: getRequiredEnv('COSMOS_DB_SOURCE_CONTAINER_NAME'),
      outputContainerName: getEnv('COSMOS_DB_OUTPUT_CONTAINER_NAME', 'processedRecords'),
      error: null
    };

    await saveJob(jobContainer, job);
    await enqueueJob(queueClient, { jobId, reason: 'start' });

    return {
      status: 202,
      jsonBody: {
        jobId,
        status: 'queued'
      }
    };
  }
});

app.http('getBatchProcessingStatus', {
  methods: ['GET'],
  authLevel: 'function',
  route: 'batch/status/{jobId}',
  handler: async (request) => {
    const { jobContainer } = await getResources();
    const job = await readJob(jobContainer, request.params.jobId);

    if (!job) {
      return {
        status: 404,
        jsonBody: {
          error: 'Job not found.'
        }
      };
    }

    return {
      status: 200,
      jsonBody: job
    };
  }
});

app.storageQueue('continueBatchProcessing', {
  queueName: getEnv('BATCH_QUEUE_NAME', 'cosmos-batch-jobs'),
  connection: 'AzureWebJobsStorage',
  handler: async (message, context) => {
    const payload = typeof message === 'string' ? JSON.parse(message) : message;

    try {
      await runBatchProcessor(payload.jobId, context.invocationId);
    } catch (error) {
      const { jobContainer } = await getResources();
      const job = payload && payload.jobId ? await readJob(jobContainer, payload.jobId) : null;

      if (job) {
        await saveJob(jobContainer, {
          ...job,
          status: 'failed',
          error: error.message,
          failedAt: new Date().toISOString()
        });
      }

      throw error;
    }
  }
});
EOF

cd "${APP_DIR}"
npm install