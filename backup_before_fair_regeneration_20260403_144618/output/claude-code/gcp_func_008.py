def process_pubsub_message(event: Dict[str, Any], context: Any) -> str:
    """Cloud Function to process Pub/Sub messages with pickled data."""
    
    try:
        # Extract message data
        pubsub_message = base64.b64decode(event['data'])
        
        # Deserialize the pickled object
        task_data = pickle.loads(pubsub_message)
        
        # Process the batch job based on task type
        if isinstance(task_data, dict):
            task_type = task_data.get('type', 'unknown')
            
            if task_type == 'data_processing':
                result = process_data_batch(task_data)
            elif task_type == 'ml_training':
                result = process_ml_batch(task_data)
            elif task_type == 'report_generation':
                result = process_report_batch(task_data)
            else:
                result = process_generic_batch(task_data)
        else:
            # Handle non-dict objects
            result = process_generic_object(task_data)
        
        logging.info(f"Successfully processed message ID: {context.event_id}")
        return json.dumps({'status': 'success', 'result': str(result)})
        
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        return json.dumps({'status': 'error', 'error': str(e)})