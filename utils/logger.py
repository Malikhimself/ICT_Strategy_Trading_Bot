import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name="ICT_Bot", log_file="bot.log", level=logging.INFO):
    """
    Sets up a logger with both console and file handlers.
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # File Handler (Rotating)
    # Max size 5MB, keep 5 backups
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # Add handlers if not already added
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
