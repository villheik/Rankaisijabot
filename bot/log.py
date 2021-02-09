import logging
import os
import sys
from logging import Logger, handlers
from pathlib import Path

def setupLogging():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)

    format_string = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    log_format = logging.Formatter(format_string)

    log_file = Path("logs", "bot.log")
    log_file.parent.mkdir(exist_ok=True)
    
    handler = logging.FileHandler(filename=log_file, encoding='utf-8', mode='w')
    handler.setFormatter(log_format)
    logger.addHandler(handler)