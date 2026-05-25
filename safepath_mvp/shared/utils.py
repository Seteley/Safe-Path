"""Utilidades compartidas: logging, red, archivos atomicos."""

from __future__ import annotations

import logging
import socket
import sys
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def setup_logging(name: str = "safepath", level: int = logging.INFO) -> logging.Logger:
    """Configura y retorna un logger con formato consistente.

    En desarrollo usa formato con timestamp legible.
    En CI/tests usa formato simple sin colores.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)

    if sys.stdout.isatty():
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        fmt = logging.Formatter("[%(levelname)-7s] %(message)s")

    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def get_local_ip() -> str:
    """Detecta la IP local de la maquina."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def atomic_write_json(path: str | Path, data: dict[str, Any]) -> None:
    """RNF-S04: Escribe JSON de forma atomica usando archivo temporal + os.replace.

    Escribe a un archivo temporal en el mismo directorio, luego
    lo renombra atomicamente. Si falla, limpia el archivo temporal.
    """
    path = Path(path)
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".json", prefix=".tmp_", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
