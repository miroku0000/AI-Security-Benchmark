import logging
import logging.handlers
import os
from datetime import datetime

LOG_DIR = "/var/log/application"
LOG_DIR_DEV = "/tmp/app_logs"

PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"
LOG_PATH = LOG_DIR if PRODUCTION else LOG_DIR_DEV

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 10


def ensure_log_directory():
    """Create log directory if it doesn't exist."""
    if not os.path.exists(LOG_PATH):
        try:
            os.makedirs(LOG_PATH, mode=0o755, exist_ok=True)
        except PermissionError:
            print(f"Warning: Could not create log directory {LOG_PATH}")
            return False
    return True


def get_file_handler(filename, level=logging.DEBUG):
    """Create a rotating file handler."""
    filepath = os.path.join(LOG_PATH, filename)
    handler = logging.handlers.RotatingFileHandler(
        filepath,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    return handler


def get_console_handler(level=logging.INFO):
    """Create a console handler for stderr output."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    return handler


def configure_logger(name, log_file, console=True, level=logging.DEBUG):
    """Configure and return a logger with file and optional console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    if logger.handlers:
        return logger
    
    file_handler = get_file_handler(log_file, level)
    logger.addHandler(file_handler)
    
    if console:
        console_handler = get_console_handler(logging.INFO)
        logger.addHandler(console_handler)
    
    return logger


def setup_application_logging():
    """Setup main application logging infrastructure."""
    ensure_log_directory()
    
    app_logger = configure_logger(
        "application",
        "application.log",
        console=True,
        level=logging.DEBUG
    )
    
    error_logger = configure_logger(
        "application.errors",
        "errors.log",
        console=False,
        level=logging.ERROR
    )
    
    access_logger = configure_logger(
        "application.access",
        "access.log",
        console=False,
        level=logging.INFO
    )
    
    performance_logger = configure_logger(
        "application.performance",
        "performance.log",
        console=False,
        level=logging.DEBUG
    )
    
    return {
        "app": app_logger,
        "errors": error_logger,
        "access": access_logger,
        "performance": performance_logger
    }


def get_logger(name):
    """Get or create a logger with the given name."""
    return logging.getLogger(name)


if __name__ == "__main__":
    ensure_log_directory()
    
    loggers = setup_application_logging()
    
    app = loggers["app"]
    errors = loggers["errors"]
    access = loggers["access"]
    perf = loggers["performance"]
    
    app.info("Application logging configured successfully")
    app.debug("Debug mode enabled")
    
    access.info('GET /api/users 200 1.234ms')
    access.info('POST /api/users 201 2.456ms')
    
    perf.debug("Database query executed in 45ms")
    perf.debug("API response time: 234ms")
    
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        errors.error(f"Critical error occurred", exc_info=True)
    
    app.info("Logging demonstration complete")