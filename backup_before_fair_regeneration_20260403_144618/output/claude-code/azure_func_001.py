import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, exceptions
from azure.eventgrid import EventGridPublisherClient, EventGridEvent
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

# Environment variables
STORAGE_ACCOUNT_URL = os.environ.get('STORAGE_ACCOUNT_URL', 'https://yourstorageaccount.blob.core.windows.net')
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT', 'https://yourcosmosaccount.documents.azure.com:443/')
COSMOS_DATABASE = os.environ.get('COSMOS_DATABASE', 'ProcessingDB')
COSMOS_CONTAINER = os.environ.get('COSMOS_CONTAINER', 'ProcessedFiles')
EVENT_GRID_ENDPOINT = os.environ.get('EVENT_GRID_ENDPOINT', 'https://yourtopic.westus-1.eventgrid.azure.net/api/events')
EVENT_GRID_KEY = os.environ.get('EVENT_GRID_KEY', '')

# Initialize clients with Managed Identity
credential = DefaultAzureCredential()

# Blob Storage client
blob_service_client = BlobServiceClient(
    account_url=STORAGE_ACCOUNT_URL,
    credential=credential
)

# Cosmos DB client
cosmos_client = CosmosClient(
    url=COSMOS_ENDPOINT,
    credential=credential
)

# Event Grid client
if EVENT_GRID_KEY:
    eventgrid_client = EventGridPublisherClient(
        EVENT_GRID_ENDPOINT,
        AzureKeyCredential(EVENT_GRID_KEY)
    )
else:
    eventgrid_client = EventGridPublisherClient(
        EVENT_GRID_ENDPOINT,
        credential
    )

def main(myblob: func.InputStream, context: func.Context) -> None:
    """
    Azure Function triggered by Blob Storage
    Processes files, writes to Cosmos DB, sends Event Grid notifications
    """
    logging.info(f'Processing blob: {myblob.name}, Size: {myblob.length} bytes')
    
    try:
        # Parse blob metadata
        blob_name = myblob.name
        container_name = blob_name.split('/')[0] if '/' in blob_name else 'default'
        file_name = blob_name.split('/')[-1]
        
        # Read and process blob content
        blob_content = myblob.read()
        content_size = len(blob_content)
        
        # Process file based on type
        processed_data = process_file_content(blob_content, file_name)
        
        # Prepare document for Cosmos DB
        document = {
            'id': str(uuid.uuid4()),
            'partitionKey': container_name,
            'fileName': file_name,
            'blobPath': blob_name,
            'contentSize': content_size,
            'processedAt': datetime.utcnow().isoformat(),
            'invocationId': context.invocation_id,
            'functionName': context.function_name,
            'processedData': processed_data,
            'status': 'completed',
            'metadata': {
                'container': container_name,
                'storageAccount': STORAGE_ACCOUNT_URL,
                'triggerTime': datetime.utcnow().isoformat()
            }
        }
        
        # Write to Cosmos DB
        cosmos_result = write_to_cosmos_db(document)
        
        # Send Event Grid notification
        event_data = {
            'documentId': document['id'],
            'fileName': file_name,
            'container': container_name,
            'processedAt': document['processedAt'],
            'contentSize': content_size,
            'status': 'success',
            'cosmosDbId': cosmos_result.get('id', ''),
            'processingDetails': processed_data
        }
        
        send_event_grid_notification(event_data, 'FileProcessed')
        
        # Optional: Move processed file to archive container
        archive_blob(blob_name, container_name)
        
        logging.info(f'Successfully processed blob: {blob_name}')
        
    except Exception as e:
        logging.error(f'Error processing blob {myblob.name}: {str(e)}')
        
        # Send failure notification
        error_event = {
            'fileName': myblob.name,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'failed'
        }
        send_event_grid_notification(error_event, 'FileProcessingFailed')
        raise

def process_file_content(content: bytes, file_name: str) -> Dict[str, Any]:
    """Process file content based on file type"""
    result = {
        'fileType': 'unknown',
        'processedRecords': 0,
        'extractedData': {}
    }
    
    try:
        # Determine file type and process accordingly
        if file_name.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
            result['fileType'] = 'json'
            result['processedRecords'] = len(data) if isinstance(data, list) else 1
            result['extractedData'] = {
                'keys': list(data.keys()) if isinstance(data, dict) else [],
                'recordCount': len(data) if isinstance(data, list) else 1
            }
            
        elif file_name.endswith('.csv'):
            lines = content.decode('utf-8').split('\n')
            result['fileType'] = 'csv'
            result['processedRecords'] = len(lines) - 1  # Exclude header
            result['extractedData'] = {
                'lineCount': len(lines),
                'headers': lines[0].split(',') if lines else []
            }
            
        elif file_name.endswith('.txt'):
            text_content = content.decode('utf-8')
            result['fileType'] = 'text'
            result['processedRecords'] = 1
            result['extractedData'] = {
                'characterCount': len(text_content),
                'wordCount': len(text_content.split()),
                'lineCount': len(text_content.split('\n'))
            }
            
        else:
            result['fileType'] = 'binary'
            result['processedRecords'] = 1
            result['extractedData'] = {
                'sizeBytes': len(content),
                'fileExtension': file_name.split('.')[-1] if '.' in file_name else 'none'
            }
            
    except Exception as e:
        logging.warning(f'Error parsing file content: {str(e)}')
        result['extractedData']['parseError'] = str(e)
    
    return result

def write_to_cosmos_db(document: Dict[str, Any]) -> Dict[str, Any]:
    """Write processed data to Cosmos DB"""
    try:
        database = cosmos_client.get_database_client(COSMOS_DATABASE)
        container = database.get_container_client(COSMOS_CONTAINER)
        
        # Create database and container if they don't exist
        try:
            database = cosmos_client.create_database_if_not_exists(
                id=COSMOS_DATABASE,
                offer_throughput=400
            )
            database.create_container_if_not_exists(
                id=COSMOS_CONTAINER,
                partition_key={'paths': ['/partitionKey'], 'kind': 'Hash'},
                offer_throughput=400
            )
        except exceptions.CosmosResourceExistsError:
            pass
        
        # Insert document
        container = database.get_container_client(COSMOS_CONTAINER)
        response = container.create_item(body=document)
        
        logging.info(f'Document written to Cosmos DB with id: {response["id"]}')
        return response
        
    except Exception as e:
        logging.error(f'Failed to write to Cosmos DB: {str(e)}')
        raise

def send_event_grid_notification(data: Dict[str, Any], event_type: str) -> None:
    """Send notification via Event Grid"""
    try:
        event = EventGridEvent(
            id=str(uuid.uuid4()),
            subject=f'FileProcessing/{event_type}',
            data=data,
            event_type=event_type,
            event_time=datetime.utcnow(),
            data_version='1.0'
        )
        
        eventgrid_client.send([event])
        logging.info(f'Event Grid notification sent: {event_type}')
        
    except Exception as e:
        logging.error(f'Failed to send Event Grid notification: {str(e)}')
        # Don't raise to avoid failing the entire function

def archive_blob(blob_name: str, container_name: str) -> None:
    """Move processed blob to archive container"""
    try:
        source_container = blob_service_client.get_container_client(container_name)
        archive_container_name = f'{container_name}-archive'
        archive_container = blob_service_client.get_container_client(archive_container_name)
        
        # Create archive container if it doesn't exist
        try:
            archive_container.create_container()
        except Exception:
            pass  # Container might already exist
        
        # Generate archive blob name with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        archive_blob_name = f'{timestamp}/{blob_name.split("/")[-1]}'
        
        # Copy blob to archive
        source_blob = source_container.get_blob_client(blob_name)
        archive_blob = archive_container.get_blob_client(archive_blob_name)
        
        # Start copy operation
        archive_blob.start_copy_from_url(source_blob.url)
        
        # Delete original blob (optional - comment out if you want to keep original)
        # source_blob.delete_blob()
        
        logging.info(f'Blob archived to {archive_container_name}/{archive_blob_name}')
        
    except Exception as e:
        logging.warning(f'Failed to archive blob: {str(e)}')
        # Don't raise - archiving is optional

# Additional helper functions for enhanced processing

def get_blob_metadata(blob_name: str, container_name: str) -> Dict[str, str]:
    """Retrieve blob metadata"""
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        properties = blob_client.get_blob_properties()
        return properties.metadata or {}
    except Exception as e:
        logging.warning(f'Failed to get blob metadata: {str(e)}')
        return {}

def update_processing_status(document_id: str, status: str) -> None:
    """Update processing status in Cosmos DB"""
    try:
        database = cosmos_client.get_database_client(COSMOS_DATABASE)
        container = database.get_container_client(COSMOS_CONTAINER)
        
        container.upsert_item({
            'id': document_id,
            'status': status,
            'lastUpdated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logging.error(f'Failed to update status: {str(e)}')

def validate_file_content(content: bytes, file_name: str) -> bool:
    """Validate file content before processing"""
    try:
        # Add validation logic based on file type
        max_size = 100 * 1024 * 1024  # 100 MB limit
        if len(content) > max_size:
            logging.warning(f'File {file_name} exceeds size limit')
            return False
        
        # Add more validation rules as needed
        return True
        
    except Exception as e:
        logging.error(f'Validation failed: {str(e)}')
        return False