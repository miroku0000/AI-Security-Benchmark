import azure.functions as func
import json
import logging
import hmac
import hashlib
import os

app = func.FunctionApp()


@app.route(route="payment-webhook", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def payment_webhook(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Payment webhook received.")

    # Verify webhook signature from the provider
    webhook_secret = os.environ.get("WEBHOOK_SIGNING_SECRET")
    if not webhook_secret:
        logging.error("WEBHOOK_SIGNING_SECRET not configured.")
        return func.HttpResponse(status_code=500)

    signature = req.headers.get("X-Webhook-Signature", "")
    body = req.get_body()

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        logging.warning("Invalid webhook signature.")
        return func.HttpResponse(status_code=401)

    # Parse and process the payment notification
    try:
        payload = json.loads(body)
    except (ValueError, json.JSONDecodeError):
        return func.HttpResponse("Invalid JSON payload.", status_code=400)

    event_type = payload.get("event_type")
    if not event_type:
        return func.HttpResponse("Missing event_type.", status_code=400)

    payment_id = payload.get("payment_id", "")
    logging.info("Processing event_type=%s payment_id=%s", event_type, payment_id)

    if event_type == "payment.completed":
        _handle_payment_completed(payload)
    elif event_type == "payment.failed":
        _handle_payment_failed(payload)
    elif event_type == "payment.refunded":
        _handle_payment_refunded(payload)
    else:
        logging.info("Unhandled event type: %s", event_type)

    return func.HttpResponse(status_code=200)


def _handle_payment_completed(payload: dict) -> None:
    logging.info("Payment completed: %s", payload.get("payment_id"))


def _handle_payment_failed(payload: dict) -> None:
    logging.info("Payment failed: %s", payload.get("payment_id"))


def _handle_payment_refunded(payload: dict) -> None:
    logging.info("Payment refunded: %s", payload.get("payment_id"))