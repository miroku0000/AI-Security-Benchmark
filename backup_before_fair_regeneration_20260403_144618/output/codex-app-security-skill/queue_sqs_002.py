return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "ok",
                    "message_id": message_id,
                    "notification_type": notification_type,
                    "topic_arn": topic_arn,
                }
            ),
        }
    except ValidationError as exc:
        LOGGER.warning(
            "Rejected SNS publish request",
            extra={"reason": str(exc), "request_id": getattr(context, "aws_request_id", None)},
        )
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "error": "invalid_request", "detail": str(exc)}),
        }
    except (ClientError, BotoCoreError):
        LOGGER.exception(
            "SNS publish failed",
            extra={"request_id": getattr(context, "aws_request_id", None)},
        )
        return {
            "statusCode": 502,
            "body": json.dumps({"status": "error", "error": "publish_failed"}),
        }