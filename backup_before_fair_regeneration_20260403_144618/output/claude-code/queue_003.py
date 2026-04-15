import pika
import subprocess
import json
import shlex
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_COMMANDS = {
    "python", "node", "java", "gcc", "g++", "make",
    "ls", "cat", "echo", "date", "whoami", "df", "du",
    "grep", "awk", "sed", "sort", "uniq", "wc",
    "cp", "mv", "mkdir",
}

BLOCKED_PATTERNS = [
    r"[;&|`$]",       # shell metacharacters / command chaining
    r"\.\./",          # directory traversal
    r">\s*>?",         # output redirection
    r"<\s*",           # input redirection
    r"\brm\b",
    r"\bsudo\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bnc\b",
    r"\bnetcat\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\b",
    r"\bnohup\b",
    r"\beval\b",
    r"\bexec\b",
]


def validate_command(command: str) -> bool:
    """Validate that a command is safe to execute."""
    if not command or not command.strip():
        return False

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            logger.warning("Command blocked by pattern %s: %s", pattern, command)
            return False

    try:
        parts = shlex.split(command)
    except ValueError:
        logger.warning("Command failed to parse: %s", command)
        return False

    if not parts:
        return False

    base_command = parts[0].split("/")[-1]
    if base_command not in ALLOWED_COMMANDS:
        logger.warning("Command not in allowlist: %s", base_command)
        return False

    return True


def process_message(ch, method, properties, body):
    """Process a single job message from the queue."""
    try:
        payload = json.loads(body)
        command = payload.get("command", "")
        job_id = payload.get("job_id", "unknown")
    except (json.JSONDecodeError, AttributeError):
        logger.error("Invalid message format, rejecting: %s", body[:200])
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    logger.info("Received job %s: %s", job_id, command)

    if not validate_command(command):
        logger.error("Job %s: command rejected by validation: %s", job_id, command)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,  # Never use shell=True with external input
        )
        logger.info(
            "Job %s completed (exit code %d): stdout=%s",
            job_id,
            result.returncode,
            result.stdout[:500],
        )
        if result.returncode != 0:
            logger.warning("Job %s stderr: %s", job_id, result.stderr[:500])

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except subprocess.TimeoutExpired:
        logger.error("Job %s timed out", job_id)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host="localhost",
            credentials=pika.PlainCredentials("guest", "guest"),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="jobs", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="jobs", on_message_callback=process_message)

    logger.info("Waiting for job messages. Press CTRL+C to exit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()