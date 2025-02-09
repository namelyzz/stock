import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

def load_cache(path: str, ttl_hours: int = 24):
    path = Path(path)
    if not path.exists():
        return None

    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if datetime.now() - mtime > timedelta(hours=ttl_hours):
        return None

    with open(path, "rb") as f:
        return pickle.load(f)

def save_cache(path: str, data: Any):
    path = Path(path)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(data, f)