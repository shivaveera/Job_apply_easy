"""Centralized logging configuration for the job bot."""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "siva-job-bot",
    log_dir: str = "data/logs",
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return the application logger.

    Outputs to both console (colored) and rotating file.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Console handler with color formatting
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler with rotation
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        Path(log_dir) / "bot.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
log = setup_logger()
