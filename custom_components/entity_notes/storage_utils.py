"""Validation and atomic JSON writes, independent of Home Assistant."""
import json
import math
import os
from pathlib import Path
import tempfile


def validate_notes(data):
    """Validate legacy string notes and timestamped notes before publishing."""
    if not isinstance(data, dict):
        raise ValueError("Notes must be an object")
    for key in ("entity_notes", "device_notes"):
        notes = data.get(key, {})
        if not isinstance(notes, dict):
            raise ValueError(f"{key} must be an object")
        for item_id, note in notes.items():
            if not isinstance(item_id, str) or not item_id:
                raise ValueError("Note IDs must be non-empty strings")
            if isinstance(note, str):
                continue
            if not isinstance(note, dict) or not isinstance(note.get("text"), str):
                raise ValueError(f"Invalid note for {item_id}")
            timestamp = note.get("updated_at")
            if timestamp is not None and (
                isinstance(timestamp, bool) or not isinstance(timestamp, (int, float))
                or not math.isfinite(timestamp) or timestamp < 0
            ):
                raise ValueError(f"Invalid timestamp for {item_id}")


def atomic_write_json(path, data):
    """Write and validate a same-directory temporary file before replacement."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        with temporary.open(encoding="utf-8") as handle:
            json.load(handle)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
