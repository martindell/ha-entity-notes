"""Constants for Entity Notes component."""

DOMAIN = "entity_notes"

STORAGE_VERSION = 1
STORAGE_KEY = "entity_notes.notes"
MAX_NOTE_LENGTH = 200

# Configuration keys
CONF_DEBUG_LOGGING = "debug_logging"
CONF_MAX_NOTE_LENGTH = "max_note_length"
CONF_AUTO_BACKUP = "auto_backup"
CONF_HIDE_BUTTONS_WHEN_EMPTY = "hide_buttons_when_empty"

# Events
EVENT_NOTES_UPDATED = "entity_notes_updated"

# Services
SERVICE_SET_NOTE = "set_note"
SERVICE_GET_NOTE = "get_note"
SERVICE_DELETE_NOTE = "delete_note"
SERVICE_LIST_NOTES = "list_notes"
SERVICE_BACKUP_NOTES = "backup_notes"
SERVICE_RESTORE_NOTES = "restore_notes"

# Default configuration values
DEFAULT_DEBUG_LOGGING = False
DEFAULT_MAX_NOTE_LENGTH = 200
DEFAULT_AUTO_BACKUP = True
DEFAULT_HIDE_BUTTONS_WHEN_EMPTY = False  # Default to always show buttons

# Frontend
FRONTEND_JS_PATH = "entity-notes.js"
