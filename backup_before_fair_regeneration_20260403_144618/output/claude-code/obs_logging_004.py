import logging
import os
import stat
from logging.handlers import RotatingFileHandler

LOG_DIR = "/var/log/myapp"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5
LOG_FILE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR  # 0o600 - owner read/write only
LOG_DIR_PERMISSIONS = stat.S_IRWXU  # 0o700 - owner full access only


def setup_logging():
    os.makedirs(LOG_DIR, mode=LOG_DIR_PERMISSIONS, exist_ok=True)
    os.chmod(LOG_DIR, LOG_DIR_PERMISSIONS)

    logger = logging.getLogger("myapp")
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
    )
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    os.chmod(LOG_FILE, LOG_FILE_PERMISSIONS)

    return logger


def main():
    logger = setup_logging()

    logger.info("Application started")
    logger.debug("Debug message for troubleshooting")
    logger.warning("This is a warning")
    logger.error("An error occurred")
    logger.critical("Critical failure")

    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("Caught an exception")

    logger.info("Application finished")


if __name__ == "__main__":
    main()