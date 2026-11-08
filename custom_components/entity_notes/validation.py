"""Strict input validation shared by REST and service handlers."""
from collections.abc import Mapping
import re


def validate_target(note_type, item_id):
    """Reject missing, non-string and malformed identifiers without coercion."""
    if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
        raise ValueError(f"{note_type}_id must be a non-empty string")
    if note_type == "entity" and not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", item_id):
        raise ValueError("entity_id must have the form domain.object_id")


def validate_note_payload(data):
    """Require an explicit string; an explicit empty string still clears a note."""
    if not isinstance(data, Mapping):
        raise ValueError("Request body must be an object")
    if "note" not in data or not isinstance(data["note"], str):
        raise ValueError("note is required and must be a string")
    if "user_name" in data and not isinstance(data["user_name"], str):
        raise ValueError("user_name must be a string")
    return data["note"]
