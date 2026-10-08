"""Persistencia y gestión de sesiones de trabajo (Workspace) en formato JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def save_workspace_file(file_path: str, workspace_data: Dict[str, Any]) -> None:
    """Guarda la configuración del esclavo y registros a un archivo JSON."""
    path = Path(file_path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(workspace_data, f, indent=2, ensure_ascii=False)


def load_workspace_file(file_path: str) -> Dict[str, Any]:
    """Carga un archivo de proyecto JSON validando su estructura básica."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data
