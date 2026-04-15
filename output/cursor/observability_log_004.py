import logging
import logging.config
import os
from pathlib import Path

LOG_DIRECTORY = "/var/log/application"


def build_logging_config(
    log_directory: str = LOG_DIRECTORY,
    root_level: str = "INFO",
    max_bytes: int = 50 * 1024 * 1024,
    backup_count: int = 10,
) -> dict:
    Path(log_directory).mkdir(parents=True, exist_ok=True)
    app_log = os.path.join(log_directory, "application.log")
    err_log = os.path.join(log_directory, "error.log")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "production": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(process)d | "
                    "%(threadName)s | %(filename)s:%(lineno)d | %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "application_rotating": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": root_level,
                "formatter": "production",
                "filename": app_log,
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
            "error_rotating": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "production",
                "filename": err_log,
                "maxBytes": max(10 * 1024 * 1024, max_bytes // 5),
                "backupCount": max(5, backup_count // 2),
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": root_level,
            "handlers": ["application_rotating", "error_rotating"],
        },
    }


def configure_production_logging(**kwargs) -> None:
    logging.config.dictConfig(build_logging_config(**kwargs))


if __name__ == "__main__":
    configure_production_logging()
    log = logging.getLogger(__name__)
    log.info("Application logging initialized.")
    log.error("Example error record for verification.")