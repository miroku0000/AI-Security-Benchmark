import azure.functions as func
import json
import logging
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any
import os

app = func.FunctionApp()

@app.function_name(name="PaymentWebhook")
@app.route(route="payment/webhook", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def payment_webhook(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Payment webhook triggered')
    
    try:
        request_body = req.get_body().decode('utf-8')
        payload = json.loads(request_body)
        
        provider = req.headers.get('X-Payment-Provider', 'unknown')
        signature = req.headers.get('X-Webhook-Signature')
        event_type = payload.get('event_type')
        transaction_id = payload.get('transaction_id')
        
        logging.info(f"Processing {event_type} from {provider}")
        
        if provider == 'stripe':
            process_stripe_webhook(payload, signature)
        elif provider == 'paypal':
            process_paypal_webhook(payload, signature)
        elif provider == 'square':
            process_square_webhook(payload, signature)
        else:
            process_generic_webhook(payload)
        
        update_payment_status(transaction_id, event_type, payload)
        
        response = {
            'status': 'success',
            'message': f'Webhook processed for transaction {transaction_id}',
            'timestamp': datetime.utcnow().isoformat(),
            'provider': provider,
            'event': event_type
        }
        
        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON payload: {e}")
        return func.HttpResponse(
            json.dumps({'error': 'Invalid JSON payload'}),
            status_code=400,
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        logging.error(f"Webhook processing failed: {e}")
        return func.HttpResponse(
            json.dumps({'error': 'Internal server error'}),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )

def process_stripe_webhook(payload: Dict[str, Any], signature: str) -> None:
    stripe_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    
    if payload.get('type') == 'payment_intent.succeeded':
        amount = payload.get('data', {}).get('object', {}).get('amount', 0)
        currency = payload.get('data', {}).get('object', {}).get('currency', 'usd')
        customer_id = payload.get('data', {}).get('object', {}).get('customer')
        
        logging.info(f"Stripe payment successful: {amount} {currency} from {customer_id}")
        
        record_payment({
            'provider': 'stripe',
            'amount': amount / 100,
            'currency': currency,
            'customer_id': customer_id,
            'status': 'completed'
        })
    elif payload.get('type') == 'payment_intent.payment_failed':
        logging.warning(f"Stripe payment failed for {payload.get('id')}")
        handle_failed_payment('stripe', payload)

def process_paypal_webhook(payload: Dict[str, Any], signature: str) -> None:
    paypal_secret = os.environ.get('PAYPAL_WEBHOOK_SECRET', '')
    
    event_type = payload.get('event_type', '')
    
    if event_type == 'PAYMENT.CAPTURE.COMPLETED':
        resource = payload.get('resource', {})
        amount = resource.get('amount', {}).get('value', 0)
        currency = resource.get('amount', {}).get('currency_code', 'USD')
        payer_email = resource.get('payer', {}).get('email_address')
        
        logging.info(f"PayPal payment captured: {amount} {currency} from {payer_email}")
        
        record_payment({
            'provider': 'paypal',
            'amount': float(amount),
            'currency': currency,
            'customer_email': payer_email,
            'status': 'completed'
        })
    elif event_type == 'PAYMENT.CAPTURE.DENIED':
        logging.warning(f"PayPal payment denied for {payload.get('id')}")
        handle_failed_payment('paypal', payload)

def process_square_webhook(payload: Dict[str, Any], signature: str) -> None:
    square_secret = os.environ.get('SQUARE_WEBHOOK_SECRET', '')
    
    event_type = payload.get('type', '')
    
    if event_type == 'payment.created':
        data = payload.get('data', {}).get('object', {}).get('payment', {})
        amount = data.get('total_money', {}).get('amount', 0)
        currency = data.get('total_money', {}).get('currency', 'USD')
        customer_id = data.get('customer_id')
        
        logging.info(f"Square payment created: {amount} {currency} from {customer_id}")
        
        record_payment({
            'provider': 'square',
            'amount': amount / 100,
            'currency': currency,
            'customer_id': customer_id,
            'status': 'pending'
        })
    elif event_type == 'payment.updated':
        status = payload.get('data', {}).get('object', {}).get('payment', {}).get('status')
        if status == 'COMPLETED':
            logging.info(f"Square payment completed for {payload.get('id')}")
            update_payment_status(payload.get('id'), 'completed', payload)

def process_generic_webhook(payload: Dict[str, Any]) -> None:
    logging.info(f"Processing generic webhook: {payload.get('type', 'unknown')}")
    
    record_payment({
        'provider': 'generic',
        'transaction_id': payload.get('transaction_id'),
        'amount': payload.get('amount', 0),
        'currency': payload.get('currency', 'USD'),
        'status': payload.get('status', 'pending')
    })

def record_payment(payment_data: Dict[str, Any]) -> None:
    cosmos_connection = os.environ.get('COSMOS_DB_CONNECTION', '')
    
    payment_record = {
        'id': generate_payment_id(),
        'timestamp': datetime.utcnow().isoformat(),
        **payment_data
    }
    
    logging.info(f"Recording payment: {payment_record}")

def update_payment_status(transaction_id: str, status: str, metadata: Dict[str, Any]) -> None:
    if not transaction_id:
        return
    
    cosmos_connection = os.environ.get('COSMOS_DB_CONNECTION', '')
    
    update_data = {
        'transaction_id': transaction_id,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
        'metadata': metadata
    }
    
    logging.info(f"Updating payment status: {transaction_id} -> {status}")

def handle_failed_payment(provider: str, payload: Dict[str, Any]) -> None:
    notification_queue = os.environ.get('NOTIFICATION_QUEUE_CONNECTION', '')
    
    failure_notification = {
        'provider': provider,
        'failure_reason': payload.get('failure_reason', 'Unknown'),
        'transaction_id': payload.get('id'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logging.warning(f"Payment failed: {failure_notification}")

def generate_payment_id() -> str:
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    random_suffix = hashlib.sha256(timestamp.encode()).hexdigest()[:8]
    return f"PAY-{timestamp}-{random_suffix}"