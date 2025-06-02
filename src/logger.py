import logging
from typing import Optional


def setup_logger(name: str, level: str, log_file: str) -> logging.Logger:
    """
    Configures and returns a logger that prefixes messages with DEBUG:
    and includes timestamps.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("DEBUG: %(asctime)s %(levelname)s: %(message)s")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger
