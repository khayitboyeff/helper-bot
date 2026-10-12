"""
utils/logger.py
Butun loyiha uchun markazlashtirilgan logging tizimi.
Konsolga va faylga bir vaqtda log yozadi.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import config


def setup_logger(name: str = "YordamchiBot") -> logging.Logger:
    """Logger obyektini sozlab qaytaradi."""

    # Log fayl uchun papka yaratish
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        # Logger allaqachon sozlangan bo'lsa, qayta sozlamaymiz
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsolga chiqarish
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Faylga yozish (5MB dan oshsa, yangi faylga o'tadi, 5 ta backup saqlaydi)
    file_handler = RotatingFileHandler(
        config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
