import logging
import logging.handlers
import os

LOG_DIR = "/var/log/application"
os.makedirs(LOG_DIR, exist_ok=True)

formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s %(name)s %(process)d %(thread)d %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app_handler = logging.handlers.RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
app_handler.setLevel(logging.INFO)
app_handler.setFormatter(formatter)

error_handler = logging.handlers.RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "error.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=10,
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(app_handler)
root_logger.addHandler(error_handler)

if __name__ == "__main__":
    logger = logging.getLogger("myapp")
    logger.info("Application started")
    logger.warning("Disk usage high")
    logger.error("Connection failed")