"""Constants for the Entity Notes integration."""

DOMAIN = "entity_notes"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.notes"

# Configuration
CONF_DEBUG_LOGGING = "debug_logging"
CONF_MAX_NOTE_LENGTH = "max_note_length"
CONF_AUTO_BACKUP = "auto_backup"
CONF_HIDE_BUTTONS_WHEN_EMPTY = "hide_buttons_when_empty"

# Defaults
DEFAULT_DEBUG_LOGGING = False
DEFAULT_MAX_NOTE_LENGTH = 250
DEFAULT_AUTO_BACKUP = False
DEFAULT_HIDE_BUTTONS_WHEN_EMPTY = False

# Limits
MAX_NOTE_LENGTH = 2000

# Frontend
FRONTEND_JS_PATH = "entity-notes.js"

# Events
EVENT_NOTES_UPDATED = f"{DOMAIN}_notes_updated"

# Services
SERVICE_SET_NOTE = "set_note"
SERVICE_GET_NOTE = "get_note"
SERVICE_DELETE_NOTE = "delete_note"
SERVICE_LIST_NOTES = "list_notes"
SERVICE_BACKUP_NOTES = "backup_notes"
SERVICE_RESTORE_NOTES = "restore_notes"
