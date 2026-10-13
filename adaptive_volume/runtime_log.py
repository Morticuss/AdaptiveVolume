"""Small rotating diagnostic log; no audio is recorded."""
import logging
from logging.handlers import RotatingFileHandler
from .config import data_dir


def configure():
    logger = logging.getLogger('adaptive_volume')
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    try:
        directory = data_dir()
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(directory / 'runtime.log', maxBytes=512_000,
                                      backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(threadName)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
