"""
VELORIX — logger.py
====================
Sistem centralizat de logging.
- Scrie in consola + fisier velorix.log (rotatie automata la 5MB, 3 arhive)
- Inlocuieste print() din toata aplicatia
- Utilizare: from logger import log; log.info("mesaj")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Importam constantele fara a crea import circular
try:
    from constants import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT
except ImportError:
    LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT = "velorix.log", 5 * 1024 * 1024, 3

_LOG_PATH = os.path.join(_BASE_DIR, LOG_FILE)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler fisier (rotatie automata)
_file_handler = RotatingFileHandler(
    _LOG_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)
_file_handler.setLevel(logging.DEBUG)

# Handler consola
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
_console_handler.setLevel(logging.INFO)

# Logger radacina pentru VELORIX
log = logging.getLogger("VELORIX")
log.setLevel(logging.DEBUG)
log.addHandler(_file_handler)
log.addHandler(_console_handler)
log.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Returneaza un logger cu prefix VELORIX.<name>."""
    child = logging.getLogger(f"VELORIX.{name}")
    return child
