import logging
import os
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: Optional[str] = None) -> None:
    """
    Configure project-wide logging using a consistent format/level.

    :param level: Optional log level string; falls back to LOG_LEVEL env or INFO.
    """
    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    logging.basicConfig(
        level=resolved_level,
        format=DEFAULT_LOG_FORMAT,
    )

    # Reduce noise from third-party libraries unless explicitly overridden.
    for noisy_logger in ("botbuilder", "aiohttp.access", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
