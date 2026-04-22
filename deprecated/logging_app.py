#!/usr/bin/env python3
import argparse
import glob
import logging
import os
import stat
import sys
from logging.handlers import RotatingFileHandler


LOG_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
LOG_DIR_MODE = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP


class SecureRotatingFileHandler(RotatingFileHandler):
    def _open(self):
        stream = super()._open()
        self._chmod_log_file(self.baseFilename)
        return stream

    def doRollover(self):
        super().doRollover()
        paths = [self.baseFilename]
        paths.extend(glob.glob(f"{self.baseFilename}.*"))
        for path in paths:
            if os.path.isfile(path):
                self._chmod_log_file(path)

    @staticmethod
    def _chmod_log_file(path):
        try:
            os.chmod(path, LOG_FILE_MODE)
        except OSError:
            pass


def configure_logging(log_dir, max_bytes, backup_count, level=logging.INFO):
    os.makedirs(log_dir, mode=LOG_DIR_MODE, exist_ok=True)
    try:
        os.chmod(log_dir, LOG_DIR_MODE)
    except OSError:
        pass

    log_path = os.path.join(log_dir, "app.log")

    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = SecureRotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    return log_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-dir",
        default=os.environ.get("APP_LOG_DIR", "logs"),
        help="Directory for log files (or set APP_LOG_DIR)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=1_048_576,
        help="Max size per log file before rotation",
    )
    parser.add_argument(
        "--backups",
        type=int,
        default=5,
        help="Number of rotated backup files to keep",
    )
    parser.add_argument(
        "--level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = parser.parse_args()

    level = getattr(logging, args.level)
    log_path = configure_logging(args.log_dir, args.max_bytes, args.backups, level=level)
    log = logging.getLogger("app")

    log.info("Application started; logging to %s", log_path)
    log.debug("Debug message")
    log.warning("Example warning")
    log.info("Done.")


if __name__ == "__main__":
    main()
