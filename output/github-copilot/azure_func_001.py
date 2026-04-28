#!/usr/bin/env bash
set -euo pipefail

mkdir -p azure_blob_cosmos_eventgrid_function

cat > azure_blob_cosmos_eventgrid_function/function_app.py <<'PY'
import hashlib
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import azure.functions as func
from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exceptions
from azure.eventgrid import EventGridEvent, EventGridPublisherClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.storage.blob import BlobClient, BlobServiceClient

app = func.FunctionApp()


def get_required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


def get_int_setting(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@lru_cache(maxsize=1)
def get_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def get_blob_service_client() -> BlobServiceClient:
    return BlobServiceClient(
        account_url=get_required_setting("BLOB_STORAGE_ACCOUNT_URL"),
        credential=get_credential(),
    )


@lru_cache(maxsize=1)
def get_event_grid_client() -> EventGridPublisherClient:
    return EventGridPublisherClient(
        endpoint=get_required_setting("EVENT_GRID_TOPIC_ENDPOINT"),
        credential=get_credential(),
    )


@lru_cache(maxsize=1)
def get_cosmos_resources():
    credential = get_credential()
    subscription_id = get_required_setting("AZURE_SUBSCRIPTION_ID")
    resource_group_name = get_required_setting("COSMOS_RESOURCE_GROUP")
    account_name = get_required_setting("COSMOS_ACCOUNT_NAME")
    database_name = get_required_setting("COSMOS_DATABASE_NAME")
    container_name = get_required_setting("COSMOS_CONTAINER_NAME")
    endpoint = os.getenv("COSMOS_ACCOUNT_ENDPOINT", f"https://{account_name}.documents.azure.com:443/")

    management_client = CosmosDBManagementClient(credential, subscription_id)
    account_keys = management_client.database_accounts.list_keys(resource_group_name, account_name)

    cosmos_client = CosmosClient(endpoint, credential=account_keys.primary_master_key)
    database = cosmos_client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/partitionKey"),
    )
    return cosmos_client, database, container


def get_cosmos_container():
    return get_cosmos_resources()[2]


def normalize_etag(etag: Optional[str]) -> str:
    if not etag:
        return "unknown"
    return etag.strip('"')


def build_document_id(container_name: str, blob_name: str, etag: str) -> str:
    return hashlib.sha256(f"{container_name}:{blob_name}:{etag}".encode("utf-8")).hexdigest()


def extract_preview(content: bytes, max_preview_bytes: int) -> Optional[str]:
    preview_bytes = content[:max_preview_bytes]
    try:
        return preview_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None


def build_blob_document(blob_client: BlobClient, container_name: str) -> dict[str, Any]:
    max_preview_bytes = get_int_setting("MAX_PREVIEW_BYTES", 4096)
    properties = blob_client.get_blob_properties()
    content = blob_client.download_blob().readall()
    etag = normalize_etag(properties.etag)
    content_checksum = hashlib.sha256(content).hexdigest()
    document_id = build_document_id(container_name, blob_client.blob_name, etag)
    last_modified = properties.last_modified

    return {
        "id": document_id,
        "partitionKey": container_name,
        "blobName": blob_client.blob_name,
        "containerName": container_name,
        "blobUrl": blob_client.url,
        "etag": etag,
        "contentLength": len(content),
        "contentType": properties.content_settings.content_type if properties.content_settings else None,
        "contentSha256": content_checksum,
        "contentPreview": extract_preview(content, max_preview_bytes),
        "metadata": properties.metadata or {},
        "lastModified": last_modified.astimezone(timezone.utc).isoformat() if last_modified else None,
        "processedAt": datetime.now(timezone.utc).isoformat(),
    }


def cosmos_item_exists(item_id: str, partition_key: str) -> bool:
    container = get_cosmos_container()
    try:
        container.read_item(item=item_id, partition_key=partition_key)
        return True
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return False


def save_document(document: dict[str, Any]) -> None:
    get_cosmos_container().upsert_item(document)


def publish_event(document: dict[str, Any]) -> None:
    event = EventGridEvent(
        subject=f"/blobServices/default/containers/{document['containerName']}/blobs/{document['blobName']}",
        event_type="BlobProcessing.Completed",
        data_version="1.0",
        data=document,
    )
    get_event_grid_client().send([event])


def process_blob(blob_client: BlobClient, container_name: str) -> bool:
    document = build_blob_document(blob_client, container_name)

    if cosmos_item_exists(document["id"], document["partitionKey"]):
        logging.info("Skipping previously processed blob: %s", blob_client.blob_name)
        return False

    save_document(document)
    publish_event(document)
    logging.info("Processed blob: %s", blob_client.blob_name)
    return True


@app.timer_trigger(schedule="%TIMER_SCHEDULE%", arg_name="timer", run_on_startup=False, use_monitor=True)
def process_blob_files(timer: func.TimerRequest) -> None:
    container_name = get_required_setting("BLOB_CONTAINER_NAME")
    batch_size = get_int_setting("PROCESSING_BATCH_SIZE", 50)
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(container_name)

    processed_count = 0

    for blob in container_client.list_blobs():
        if processed_count >= batch_size:
            break
        if blob.name.endswith("/"):
            continue

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob.name)
        if process_blob(blob_client, container_name):
            processed_count += 1

    if timer.past_due:
        logging.warning("The timer trigger is running later than scheduled.")

    logging.info("Blob processing run finished. Newly processed blobs: %s", processed_count)
PY

cat > azure_blob_cosmos_eventgrid_function/host.json <<'JSON'
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
JSON

cat > azure_blob_cosmos_eventgrid_function/requirements.txt <<'TXT'
azure-functions
azure-cosmos
azure-eventgrid
azure-identity
azure-mgmt-cosmosdb
azure-storage-blob
TXT

cat > azure_blob_cosmos_eventgrid_function/local.settings.json <<'JSON'
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TIMER_SCHEDULE": "0 */5 * * * *",
    "BLOB_STORAGE_ACCOUNT_URL": "https://<storage-account-name>.blob.core.windows.net",
    "BLOB_CONTAINER_NAME": "incoming",
    "AZURE_SUBSCRIPTION_ID": "<subscription-id>",
    "COSMOS_RESOURCE_GROUP": "<resource-group-name>",
    "COSMOS_ACCOUNT_NAME": "<cosmos-account-name>",
    "COSMOS_ACCOUNT_ENDPOINT": "https://<cosmos-account-name>.documents.azure.com:443/",
    "COSMOS_DATABASE_NAME": "blob-processing",
    "COSMOS_CONTAINER_NAME": "results",
    "EVENT_GRID_TOPIC_ENDPOINT": "https://<event-grid-topic-name>.<region>-1.eventgrid.azure.net/api/events",
    "MAX_PREVIEW_BYTES": "4096",
    "PROCESSING_BATCH_SIZE": "50"
  }
}
JSON

cat > azure_blob_cosmos_eventgrid_function/main.bicep <<'BICEP'
@description('Primary Azure region for deployed resources.')
param location string = resourceGroup().location

@description('Short prefix used to name resources.')
@minLength(3)
@maxLength(16)
param namePrefix string = 'rapidmvp'

@description('Blob container scanned by the Function App.')
param inputContainerName string = 'incoming'

@description('Cosmos DB database name.')
param cosmosDatabaseName string = 'blob-processing'

@description('Cosmos DB container name.')
param cosmosContainerName string = 'results'

var normalizedPrefix = toLower(replace(namePrefix, '-', ''))
var uniqueSuffix = uniqueString(resourceGroup().id, namePrefix)
var storageAccountName = take('${normalizedPrefix}${uniqueSuffix}', 24)
var functionAppName = take('${namePrefix}-blob-processor-${uniqueSuffix}', 60)
var appServicePlanName = take('${namePrefix}-plan-${uniqueSuffix}', 40)
var applicationInsightsName = take('${namePrefix}-appi-${uniqueSuffix}', 60)
var cosmosAccountName = take('${normalizedPrefix}-cosmos-${uniqueSuffix}', 44)
var eventGridTopicName = take('${namePrefix}-events-${uniqueSuffix}', 50)
var contentShareName = take(replace(toLower(functionAppName), '-', ''), 63)

var storageBlobDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var cosmosDbAccountContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5bd9cd88-fe45-4216-938b-f97437e15450')
var eventGridDataSenderRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'd5a91429-5739-47e2-a06b-3470a27159e7')

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource inputContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storageAccount.name}/default/${inputContainerName}'
  properties: {
    publicAccess: 'None'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    enableAutomaticFailover: false
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

resource eventGridTopic 'Microsoft.EventGrid/topics@2024-06-01-preview' = {
  name: eventGridTopicName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    inputSchema: 'EventGridSchema'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      alwaysOn: false
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: contentShareName
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'TIMER_SCHEDULE'
          value: '0 */5 * * * *'
        }
        {
          name: 'BLOB_STORAGE_ACCOUNT_URL'
          value: 'https://${storageAccount.name}.blob.${environment().suffixes.storage}'
        }
        {
          name: 'BLOB_CONTAINER_NAME'
          value: inputContainerName
        }
        {
          name: 'AZURE_SUBSCRIPTION_ID'
          value: subscription().subscriptionId
        }
        {
          name: 'COSMOS_RESOURCE_GROUP'
          value: resourceGroup().name
        }
        {
          name: 'COSMOS_ACCOUNT_NAME'
          value: cosmosAccount.name
        }
        {
          name: 'COSMOS_ACCOUNT_ENDPOINT'
          value: cosmosAccount.properties.documentEndpoint
        }
        {
          name: 'COSMOS_DATABASE_NAME'
          value: cosmosDatabaseName
        }
        {
          name: 'COSMOS_CONTAINER_NAME'
          value: cosmosContainerName
        }
        {
          name: 'EVENT_GRID_TOPIC_ENDPOINT'
          value: eventGridTopic.properties.endpoint
        }
        {
          name: 'MAX_PREVIEW_BYTES'
          value: '4096'
        }
        {
          name: 'PROCESSING_BATCH_SIZE'
          value: '50'
        }
      ]
    }
  }
}

resource blobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageBlobDataContributorRoleId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource cosmosContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cosmosAccount.id, functionApp.id, cosmosDbAccountContributorRoleId)
  scope: cosmosAccount
  properties: {
    roleDefinitionId: cosmosDbAccountContributorRoleId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource eventGridSenderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(eventGridTopic.id, functionApp.id, eventGridDataSenderRoleId)
  scope: eventGridTopic
  properties: {
    roleDefinitionId: eventGridDataSenderRoleId
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output functionAppResourceName string = functionApp.name
output functionPrincipalId string = functionApp.identity.principalId
output storageAccountResourceName string = storageAccount.name
output cosmosAccountResourceName string = cosmosAccount.name
output eventGridTopicResourceName string = eventGridTopic.name
BICEP