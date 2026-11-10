"""Store the last verified QZ endpoint in the Windows user profile."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from qz_ws_client import normalize_endpoint


def _config_path():
    directory = os.environ.get("LOCALAPPDATA")
    if not directory:
        raise OSError("LOCALAPPDATA is unavailable.")
    return Path(directory) / "TreadCraft" / "qz_connection.json"


def load_qz_endpoint():
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("endpoint"), str):
            return normalize_endpoint(data["endpoint"])
    except (OSError, ValueError):
        pass
    return None


def save_qz_endpoint(endpoint):
    path = _config_path()
    contents = json.dumps({"endpoint": normalize_endpoint(endpoint)}) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
