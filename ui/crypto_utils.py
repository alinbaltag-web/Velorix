"""
Utilitar de criptare simetrica pentru date sensibile (credentiale API, CNP).

Cheia Fernet este generata automat la prima rulare si stocata in:
    %APPDATA%/ServiceMoto/secret.key   (Windows)
    ~/ServiceMoto/secret.key           (fallback)

Comportament backward-compatible:
    decrypt(text) returneaza text-ul original daca nu este un token Fernet valid
    (util pentru date vechi stocate plain-text inainte de implementarea criptarii).
"""

import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

_fernet = None


def _get_key_path() -> Path:
    app_data = os.environ.get("APPDATA", str(Path.home()))
    key_dir = Path(app_data) / "ServiceMoto"
    key_dir.mkdir(parents=True, exist_ok=True)
    return key_dir / "secret.key"


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        path = _get_key_path()
        if path.exists():
            key = path.read_bytes()
        else:
            key = Fernet.generate_key()
            path.write_bytes(key)
        _fernet = Fernet(key)
    return _fernet


def encrypt(text: str) -> str:
    """Cripteaza un string. Returneaza '' daca input-ul e gol."""
    if not text:
        return ""
    return _get_fernet().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(text: str) -> str:
    """
    Decripteaza un string criptat cu Fernet.
    Daca valoarea nu este un token Fernet valid (ex: date vechi plain-text),
    returneaza valoarea originala nemodificata.
    """
    if not text:
        return ""
    try:
        return _get_fernet().decrypt(text.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return text  # backward-compat: date neincriptate din baza veche
