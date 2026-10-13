import logging
import os
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(name: str = "trader") -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    rich_handler.setLevel(level)

    file_handler = logging.FileHandler(log_dir / "trader.log")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)
    return logger


log = setup_logging()
