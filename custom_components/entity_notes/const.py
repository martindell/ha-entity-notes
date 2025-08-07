
"""Constants for Entity Notes component."""

DOMAIN = "entity_notes"
STORAGE_VERSION = 1
STORAGE_KEY = "entity_notes"
MAX_NOTE_LENGTH = 200

# Events
EVENT_NOTES_UPDATED = "entity_notes_updated"

# Services
SERVICE_SET_NOTE = "set_note"
SERVICE_GET_NOTE = "get_note" 
SERVICE_DELETE_NOTE = "delete_note"
SERVICE_LIST_NOTES = "list_notes"
