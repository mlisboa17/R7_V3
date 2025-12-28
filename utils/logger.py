import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging(config: dict):
    log_folder = config.get('log_folder', 'logs')
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, 'r7_v3.log')

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))

    # File handler with daily rotation
    fh = TimedRotatingFileHandler(log_file, when='midnight', backupCount=7, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))

    # Avoid adding multiple handlers if called multiple times
    if not any(isinstance(h, TimedRotatingFileHandler) for h in logger.handlers):
        logger.addHandler(ch)
        logger.addHandler(fh)

    logger.info('[LOGGER] Logging configurado. Pasta: %s', log_folder)
    return logger