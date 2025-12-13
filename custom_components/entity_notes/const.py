"""Constants for Entity Notes component."""

DOMAIN = "entity_notes"
STORAGE_VERSION = 2
STORAGE_KEY = "entity_notes.notes"
MAX_NOTE_LENGTH = 200

# Configuration keys
CONF_DEBUG_LOGGING = "debug_logging"
CONF_MAX_NOTE_LENGTH = "max_note_length"
CONF_AUTO_BACKUP = "auto_backup"
CONF_HIDE_BUTTONS_WHEN_EMPTY = "hide_buttons_when_empty"
CONF_DELETE_NOTES_WITH_ENTITY = "delete_notes_with_entity"
CONF_DELETE_NOTES_WITH_DEVICE = "delete_notes_with_device"
CONF_ENABLE_DEVICE_NOTES = "enable_device_notes"

# Events
EVENT_NOTES_UPDATED = "entity_notes_updated"
EVENT_DEVICE_NOTES_UPDATED = "device_notes_updated"

# Services - Entity
SERVICE_SET_NOTE = "set_note"
SERVICE_GET_NOTE = "get_note"
SERVICE_DELETE_NOTE = "delete_note"
SERVICE_LIST_NOTES = "list_notes"
SERVICE_BACKUP_NOTES = "backup_notes"
SERVICE_RESTORE_NOTES = "restore_notes"

# Services - Device
SERVICE_SET_DEVICE_NOTE = "set_device_note"
SERVICE_GET_DEVICE_NOTE = "get_device_note"
SERVICE_DELETE_DEVICE_NOTE = "delete_device_note"
SERVICE_LIST_DEVICE_NOTES = "list_device_notes"

# Default configuration values
DEFAULT_DEBUG_LOGGING = False
DEFAULT_MAX_NOTE_LENGTH = 200
DEFAULT_AUTO_BACKUP = True
DEFAULT_HIDE_BUTTONS_WHEN_EMPTY = True
DEFAULT_DELETE_NOTES_WITH_ENTITY = True
DEFAULT_DELETE_NOTES_WITH_DEVICE = True
DEFAULT_ENABLE_DEVICE_NOTES = True

# File paths
FRONTEND_JS_PATH = "entity-notes.js"
