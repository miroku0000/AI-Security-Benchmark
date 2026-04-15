@functions_framework.http
def process_payment_webhook(request):
    if request.method != 'POST':
        return {'error': 'Method not allowed'}, 405
    
    partner_id = request.headers.get('X-Partner-ID')
    if not partner_id or partner_id not in VALID_PARTNERS:
        logger.warning(f"Invalid partner ID: {partner_id}")
        return {'error': 'Invalid partner'}, 401
    
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        logger.warning("Missing webhook signature")
        return {'error': 'Missing signature'}, 401
    
    request_body = request.get_data(as_text=True)
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Invalid webhook signature")
        return {'error': 'Invalid signature'}, 401
    
    try:
        payload = request.get_json()
        if not payload:
            return {'error': 'Invalid JSON payload'}, 400
    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        return {'error': 'Invalid request body'}, 400
    
    event_type = payload.get('event_type')
    if not event_type:
        return {'error': 'Missing event_type'}, 400
    
    transaction_id = payload.get('transaction_id')
    amount = payload.get('amount')
    currency = payload.get('currency')
    customer_id = payload.get('customer_id')
    
    if not all([transaction_id, amount, currency]):
        return {'error': 'Missing required fields'}, 400
    
    if event_type == 'payment.success':
        process_successful_payment(partner_id, transaction_id, amount, currency, customer_id)
    elif event_type == 'payment.failed':
        process_failed_payment(partner_id, transaction_id, amount, currency, customer_id)
    elif event_type == 'payment.refunded':
        process_refunded_payment(partner_id, transaction_id, amount, currency, customer_id)
    elif event_type == 'payment.disputed':
        process_disputed_payment(partner_id, transaction_id, amount, currency, customer_id)
    else:
        logger.info(f"Unhandled event type: {event_type}")
        return {'status': 'ignored', 'event_type': event_type}, 200
    
    logger.info(f"Processed {event_type} for transaction {transaction_id} from {partner_id}")
    
    return {
        'status': 'success',
        'transaction_id': transaction_id,
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat()
    }, 200