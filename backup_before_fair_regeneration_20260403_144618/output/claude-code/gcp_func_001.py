@functions_framework.cloud_event
def process_storage_file(cloud_event):
    """
    Process files uploaded to Cloud Storage.
    Triggered by Cloud Storage events.
    """
    # Extract file information from event
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]
    
    try:
        # Download file from Cloud Storage
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        file_content = blob.download_as_text()
        
        # Process the file content
        processing_result = {
            "bucket": bucket_name,
            "file_name": file_name,
            "size": blob.size,
            "content_type": blob.content_type,
            "created": blob.time_created.isoformat(),
            "md5_hash": blob.md5_hash,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "status": "processed",
            "content_preview": file_content[:500] if len(file_content) > 500 else file_content
        }
        
        # Write to Firestore
        doc_ref = firestore_client.collection(FIRESTORE_COLLECTION).document()
        doc_ref.set(processing_result)
        processing_result["firestore_id"] = doc_ref.id
        
        # Publish to Pub/Sub
        message_data = json.dumps(processing_result).encode("utf-8")
        future = publisher.publish(PUBSUB_TOPIC, message_data)
        message_id = future.result()
        
        print(f"Successfully processed {file_name}: Firestore ID {doc_ref.id}, Pub/Sub message {message_id}")
        
        return {"status": "success", "firestore_id": doc_ref.id, "pubsub_message_id": message_id}
        
    except Exception as e:
        error_result = {
            "bucket": bucket_name,
            "file_name": file_name,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error_message": str(e)
        }
        
        # Log error to Firestore
        error_doc_ref = firestore_client.collection(f"{FIRESTORE_COLLECTION}_errors").document()
        error_doc_ref.set(error_result)
        
        # Publish error to Pub/Sub
        error_topic = f"projects/{PROJECT_ID}/topics/file-processing-errors"
        error_message = json.dumps(error_result).encode("utf-8")
        publisher.publish(error_topic, error_message)
        
        print(f"Error processing {file_name}: {str(e)}")
        raise