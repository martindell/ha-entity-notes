"""Entity Notes integration for Home Assistant."""
import logging
import voluptuous as vol
import time
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.storage import Store
from homeassistant.components.frontend import add_extra_js_url
from aiohttp import web
import json
import os
from pathlib import Path

from .const import (
    DOMAIN,
    STORAGE_VERSION,
    STORAGE_KEY,
    MAX_NOTE_LENGTH,
    CONF_DEBUG_LOGGING,
    CONF_MAX_NOTE_LENGTH,
    CONF_AUTO_BACKUP,
    CONF_HIDE_BUTTONS_WHEN_EMPTY,
    CONF_HIDE_BUTTONS_UNTIL_FOCUS,
    CONF_DELETE_NOTES_WITH_ENTITY,
    CONF_DELETE_NOTES_WITH_DEVICE,
    CONF_ENABLE_DEVICE_NOTES,
    CONF_SHOW_MARKDOWN_TOOLBAR,
    CONF_HIDE_MARKDOWN_TOOLBAR,
    CONF_CONFIRM_DELETE,
    CONF_HIDE_PREVIEW_BUTTON,
    CONF_HIDE_MARKDOWN_HINTS,
    CONF_EMPTY_NOTE_PLACEHOLDER,
    CONF_HIDE_LAST_MODIFIED,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_AUTO_BACKUP,
    DEFAULT_HIDE_BUTTONS_WHEN_EMPTY,
    DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS,
    DEFAULT_DELETE_NOTES_WITH_ENTITY,
    DEFAULT_DELETE_NOTES_WITH_DEVICE,
    DEFAULT_ENABLE_DEVICE_NOTES,
    DEFAULT_CONFIRM_DELETE,
    DEFAULT_SHOW_MARKDOWN_TOOLBAR,
    DEFAULT_HIDE_MARKDOWN_TOOLBAR,
    DEFAULT_HIDE_PREVIEW_BUTTON,
    DEFAULT_HIDE_MARKDOWN_HINTS,
    DEFAULT_EMPTY_NOTE_PLACEHOLDER,
    DEFAULT_HIDE_LAST_MODIFIED,
    FRONTEND_JS_PATH,
    EVENT_NOTES_UPDATED,
    EVENT_DEVICE_NOTES_UPDATED,
    SERVICE_SET_NOTE,
    SERVICE_GET_NOTE,
    SERVICE_DELETE_NOTE,
    SERVICE_LIST_NOTES,
    SERVICE_BACKUP_NOTES,
    SERVICE_RESTORE_NOTES,
    SERVICE_SET_DEVICE_NOTE,
    SERVICE_GET_DEVICE_NOTE,
    SERVICE_DELETE_DEVICE_NOTE,
    SERVICE_LIST_DEVICE_NOTES,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

NOTE_TARGETS = {
    "entity": {
        "store_key": "entity_notes",
        "id_field": "entity_id",
        "event": EVENT_NOTES_UPDATED,
        "get_response_event": "entity_notes_get_response",
        "list_response_event": "entity_notes_list_response",
        "set_service": "set_note",
    },
    "device": {
        "store_key": "device_notes",
        "id_field": "device_id",
        "event": EVENT_DEVICE_NOTES_UPDATED,
        "get_response_event": "device_notes_get_response",
        "list_response_event": "device_notes_list_response",
        "set_service": "set_device_note",
    },
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Entity Notes integration from configuration.yaml."""
    # This is for backward compatibility with configuration.yaml
    # The main setup now happens in async_setup_entry
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    _LOGGER.info("Setting up Entity Notes integration")

    # Get configuration options
    options = entry.options or {}
    debug_logging = options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
    max_note_length = options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
    auto_backup = options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
    hide_buttons_when_empty = options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
    hide_buttons_until_focus = options.get(CONF_HIDE_BUTTONS_UNTIL_FOCUS, DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS)
    delete_notes_with_entity = options.get(CONF_DELETE_NOTES_WITH_ENTITY, DEFAULT_DELETE_NOTES_WITH_ENTITY)
    delete_notes_with_device = options.get(CONF_DELETE_NOTES_WITH_DEVICE, DEFAULT_DELETE_NOTES_WITH_DEVICE)
    enable_device_notes = options.get(CONF_ENABLE_DEVICE_NOTES, DEFAULT_ENABLE_DEVICE_NOTES)
    hide_markdown_toolbar = options.get(
        CONF_HIDE_MARKDOWN_TOOLBAR,
        not options.get(CONF_SHOW_MARKDOWN_TOOLBAR, DEFAULT_SHOW_MARKDOWN_TOOLBAR),
    )
    show_markdown_toolbar = not hide_markdown_toolbar
    confirm_delete = options.get(CONF_CONFIRM_DELETE, DEFAULT_CONFIRM_DELETE)
    hide_preview_button = options.get(CONF_HIDE_PREVIEW_BUTTON, DEFAULT_HIDE_PREVIEW_BUTTON)
    hide_markdown_hints = options.get(CONF_HIDE_MARKDOWN_HINTS, DEFAULT_HIDE_MARKDOWN_HINTS)
    empty_note_placeholder = options.get(CONF_EMPTY_NOTE_PLACEHOLDER, DEFAULT_EMPTY_NOTE_PLACEHOLDER)
    hide_last_modified = options.get(CONF_HIDE_LAST_MODIFIED, DEFAULT_HIDE_LAST_MODIFIED)

    if debug_logging:
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug logging enabled for Entity Notes")

    try:
        # Check for v1 storage and migrate BEFORE creating Store
        storage_path = Path(hass.config.path(".storage")) / STORAGE_KEY

        if storage_path.exists():
            try:
                # Read file asynchronously using executor
                def _read_storage():
                    with open(storage_path, 'r') as f:
                        return json.load(f)

                file_data = await hass.async_add_executor_job(_read_storage)
                file_version = file_data.get("version", 1)

                if file_version == 1:
                    _LOGGER.warning("=" * 80)
                    _LOGGER.warning("MIGRATING Entity Notes from v1 to v2")
                    _LOGGER.warning("Found storage version 1, upgrading to version 2")

                    old_data = file_data.get("data", {})
                    _LOGGER.warning("Found %d entity notes to migrate", len(old_data))

                    # Create backup asynchronously
                    try:
                        backup_path = Path(hass.config.path(".storage")) / "entity_notes.notes.backup_v1"

                        def _write_backup():
                            with open(backup_path, 'w') as f:
                                json.dump(file_data, f, indent=2)

                        await hass.async_add_executor_job(_write_backup)
                        _LOGGER.warning("Created backup at: %s", backup_path)
                    except Exception as backup_error:
                        _LOGGER.error("Failed to create backup: %s", backup_error)

                    # Prepare migrated data in v2 format
                    migrated_data = {
                        "version": STORAGE_VERSION,
                        "minor_version": 1,
                        "key": STORAGE_KEY,
                        "data": {
                            "entity_notes": old_data.copy(),
                            "device_notes": {}
                        }
                    }

                    # Write migrated file asynchronously
                    def _write_migrated():
                        with open(storage_path, 'w') as f:
                            json.dump(migrated_data, f, indent=2)

                    await hass.async_add_executor_job(_write_migrated)

                    _LOGGER.warning("Successfully migrated %d entity notes to v2", len(old_data))
                    _LOGGER.warning("=" * 80)

            except Exception as e:
                _LOGGER.error("Error during migration: %s", e)
                import traceback
                _LOGGER.error("Traceback: %s", traceback.format_exc())

        # Initialize storage (now v2 format if migration happened)
        _LOGGER.debug("Initializing storage")
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        # Load existing notes
        try:
            stored_data = await store.async_load()

            # Extract entity and device notes from stored data
            entity_notes_data = stored_data.get("entity_notes", {}) if stored_data else {}
            device_notes_data = stored_data.get("device_notes", {}) if stored_data else {}

            _LOGGER.info("Loaded %d entity notes and %d device notes",
                         len(entity_notes_data), len(device_notes_data))
        except Exception as e:
            _LOGGER.error("=" * 80)
            _LOGGER.error("EXCEPTION WHILE LOADING NOTES STORAGE")
            _LOGGER.error("Error type: %s", type(e).__name__)
            _LOGGER.error("Error message: %s", str(e))
            import traceback
            _LOGGER.error("Full traceback:\n%s", traceback.format_exc())
            _LOGGER.error("=" * 80)
            _LOGGER.error(
                "Entity Notes setup aborted to avoid overwriting existing note storage. "
                "Check .storage/%s before reloading the integration.",
                STORAGE_KEY,
            )
            return False

        # Store the configuration and data in hass.data
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN] = {
            "store": store,
            "entity_notes": entity_notes_data,
            "device_notes": device_notes_data,
            "config": {
                CONF_DEBUG_LOGGING: debug_logging,
                CONF_MAX_NOTE_LENGTH: max_note_length,
                CONF_AUTO_BACKUP: auto_backup,
                CONF_HIDE_BUTTONS_WHEN_EMPTY: hide_buttons_when_empty,
                CONF_HIDE_BUTTONS_UNTIL_FOCUS: hide_buttons_until_focus,
                CONF_DELETE_NOTES_WITH_ENTITY: delete_notes_with_entity,
                CONF_DELETE_NOTES_WITH_DEVICE: delete_notes_with_device,
                CONF_ENABLE_DEVICE_NOTES: enable_device_notes,
                CONF_SHOW_MARKDOWN_TOOLBAR: show_markdown_toolbar,
                CONF_HIDE_MARKDOWN_TOOLBAR: hide_markdown_toolbar,
                CONF_CONFIRM_DELETE: confirm_delete,
                CONF_HIDE_PREVIEW_BUTTON: hide_preview_button,
                CONF_HIDE_MARKDOWN_HINTS: hide_markdown_hints,
                CONF_EMPTY_NOTE_PLACEHOLDER: empty_note_placeholder,
                CONF_HIDE_LAST_MODIFIED: hide_last_modified,
            },
            "entry_id": entry.entry_id,
            "entity_listener_remove": None,  # Will store the entity event listener removal callable
            "device_listener_remove": None,  # Will store the device event listener removal callable
        }

        # Register the API views
        hass.http.register_view(EntityNotesView())
        _LOGGER.debug("EntityNotesView registered")

        if enable_device_notes:
            hass.http.register_view(DeviceNotesView())
            _LOGGER.debug("DeviceNotesView registered")

        # Register the render view for Live Preview
        hass.http.register_view(EntityNotesRenderView())
        _LOGGER.debug("EntityNotesRenderView registered")

        # Register the JavaScript file serving view
        hass.http.register_view(EntityNotesJSView())
        _LOGGER.debug("EntityNotesJSView registered")

        # Add JavaScript to frontend - SINGLE STATIC URL (no cache busting to prevent multiple versions)
        js_url = "/api/entity_notes/entity-notes.js"
        add_extra_js_url(hass, js_url)
        _LOGGER.debug("Frontend resource registered: %s", js_url)

        # Register services
        await async_register_services(hass)

        # Set up entity removal tracking if enabled
        if delete_notes_with_entity:
            async def entity_removed_listener(event):
                """Handle entity removal events."""
                entity_id = event.data.get("entity_id")
                old_state = event.data.get("old_state")
                new_state = event.data.get("new_state")

                # Entity was removed if new_state is None and old_state existed
                if new_state is None and old_state is not None and entity_id:
                    entity_notes_data = hass.data[DOMAIN]["entity_notes"]

                    # Check if we have a note for this entity
                    if entity_id in entity_notes_data:
                        store = hass.data[DOMAIN]["store"]
                        del entity_notes_data[entity_id]

                        # Save both entity and device notes
                        await store.async_save({
                            "entity_notes": entity_notes_data,
                            "device_notes": hass.data[DOMAIN]["device_notes"]
                        })

                        # Fire event
                        hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": ""})

                        if debug_logging:
                            _LOGGER.debug("Deleted note for removed entity: %s", entity_id)
                        else:
                            _LOGGER.info("Deleted note for removed entity: %s", entity_id)

            # Listen for state_changed events and store the removal callable
            entity_listener_remove = hass.bus.async_listen("state_changed", entity_removed_listener)
            hass.data[DOMAIN]["entity_listener_remove"] = entity_listener_remove
            _LOGGER.debug("Entity removal tracking enabled")

        # Set up device removal tracking if enabled
        if enable_device_notes and delete_notes_with_device:
            from homeassistant.helpers import device_registry as dr

            async def device_removed_listener(event):
                """Handle device removal events."""
                if event.data.get("action") == "remove":
                    device_id = event.data.get("device_id")

                    if device_id:
                        device_notes_data = hass.data[DOMAIN]["device_notes"]

                        # Check if we have a note for this device
                        if device_id in device_notes_data:
                            store = hass.data[DOMAIN]["store"]
                            del device_notes_data[device_id]

                            # Save both entity and device notes
                            await store.async_save({
                                "entity_notes": hass.data[DOMAIN]["entity_notes"],
                                "device_notes": device_notes_data
                            })

                            # Fire event
                            hass.bus.async_fire(EVENT_DEVICE_NOTES_UPDATED, {"device_id": device_id, "note": ""})

                            if debug_logging:
                                _LOGGER.debug("Deleted note for removed device: %s", device_id)
                            else:
                                _LOGGER.info("Deleted note for removed device: %s", device_id)

            # Listen for device registry events
            device_listener_remove = hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, device_removed_listener)
            hass.data[DOMAIN]["device_listener_remove"] = device_listener_remove
            _LOGGER.debug("Device removal tracking enabled")

        _LOGGER.info("Entity Notes integration setup completed successfully")
        return True

    except Exception as e:
        _LOGGER.error("Critical error in Entity Notes setup: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Entity Notes integration")

    try:
        # Remove event listeners if they exist
        if DOMAIN in hass.data:
            if hass.data[DOMAIN].get("entity_listener_remove"):
                hass.data[DOMAIN]["entity_listener_remove"]()
                _LOGGER.debug("Entity removal listener removed")

            if hass.data[DOMAIN].get("device_listener_remove"):
                hass.data[DOMAIN]["device_listener_remove"]()
                _LOGGER.debug("Device removal listener removed")

        # Remove services
        services_to_remove = [
            SERVICE_SET_NOTE,
            SERVICE_GET_NOTE,
            SERVICE_DELETE_NOTE,
            SERVICE_LIST_NOTES,
            SERVICE_BACKUP_NOTES,
            SERVICE_RESTORE_NOTES,
            SERVICE_SET_DEVICE_NOTE,
            SERVICE_GET_DEVICE_NOTE,
            SERVICE_DELETE_DEVICE_NOTE,
            SERVICE_LIST_DEVICE_NOTES,
        ]

        for service in services_to_remove:
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

        # Clean up data
        hass.data.pop(DOMAIN, None)

        _LOGGER.info("Entity Notes integration unloaded successfully")
        return True

    except Exception as e:
        _LOGGER.error("Error unloading Entity Notes: %s", e)
        return False


def _note_target(note_type):
    """Return metadata for entity or device notes."""
    return NOTE_TARGETS[note_type]


def _notes_data(hass: HomeAssistant, note_type):
    """Return the in-memory notes dictionary for a note type."""
    return hass.data[DOMAIN][_note_target(note_type)["store_key"]]


def _note_log_target(note_type, item_id):
    """Return a readable target for log messages."""
    if note_type == "device":
        return f"device {item_id}"
    return item_id


def _note_text_and_updated(raw_note):
    """Normalize old string notes and current dict notes."""
    if isinstance(raw_note, dict):
        return raw_note.get("text", ""), raw_note.get("updated_at")
    return raw_note, None


async def _save_notes(hass: HomeAssistant) -> None:
    """Persist entity and device notes together."""
    await hass.data[DOMAIN]["store"].async_save({
        "entity_notes": hass.data[DOMAIN]["entity_notes"],
        "device_notes": hass.data[DOMAIN]["device_notes"],
    })


def _render_note(hass: HomeAssistant, note_type, item_id, note, user_name):
    """Render a note as a Home Assistant template."""
    rendered_note = note
    if not note:
        return rendered_note

    target = _note_target(note_type)
    try:
        from homeassistant.helpers.template import Template
        tpl = Template(note, hass)
        variables = {target["id_field"]: item_id, "user": user_name}
        rendered_note = str(tpl.async_render(variables, parse_result=False))
    except Exception as e:
        if note_type == "device":
            _LOGGER.warning("Failed to render template for device %s: %s", item_id, e)
        else:
            _LOGGER.warning("Failed to render template for %s: %s", item_id, e)

    return rendered_note


def _log_note_change(hass: HomeAssistant, log_changes, message, *args) -> None:
    """Log service changes at info level and REST changes only in debug mode."""
    if log_changes:
        _LOGGER.info(message, *args)
    elif hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]:
        _LOGGER.debug(message, *args)


async def _set_note(hass: HomeAssistant, note_type, item_id, note, log_changes=True):
    """Set or remove a note and return its saved state."""
    target = _note_target(note_type)
    notes_data = _notes_data(hass, note_type)
    max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]
    note = str(note or "")

    if len(note) > max_length:
        note = note[:max_length]
        _LOGGER.warning(
            "Note truncated to %d characters for %s",
            max_length,
            _note_log_target(note_type, item_id),
        )

    note_text = note.strip()
    updated_at = None
    if note_text:
        updated_at = int(time.time())
        notes_data[item_id] = {
            "text": note_text,
            "updated_at": updated_at,
        }
        _log_note_change(hass, log_changes, "Set note for %s", _note_log_target(note_type, item_id))
    else:
        notes_data.pop(item_id, None)
        _log_note_change(hass, log_changes, "Removed note for %s", _note_log_target(note_type, item_id))

    await _save_notes(hass)
    hass.bus.async_fire(target["event"], {target["id_field"]: item_id, "note": note_text})
    return note_text, updated_at


async def _delete_note(hass: HomeAssistant, note_type, item_id, log_changes=True):
    """Delete a note if it exists."""
    target = _note_target(note_type)
    notes_data = _notes_data(hass, note_type)
    if item_id not in notes_data:
        return False

    del notes_data[item_id]
    await _save_notes(hass)
    hass.bus.async_fire(target["event"], {target["id_field"]: item_id, "note": ""})
    _log_note_change(hass, log_changes, "Deleted note for %s", _note_log_target(note_type, item_id))
    return True


async def async_register_services(hass: HomeAssistant) -> None:
    """Register the Entity Notes services."""

    async def handle_set_note_service(call, note_type):
        """Set a note for an entity or device."""
        target = _note_target(note_type)
        item_id = call.data.get(target["id_field"])
        if not item_id:
            _LOGGER.error("No %s provided for %s service", target["id_field"], target["set_service"])
            return

        await _set_note(hass, note_type, item_id, call.data.get("note", ""))

    async def handle_get_note_service(call, note_type):
        """Get a note for an entity or device."""
        target = _note_target(note_type)
        item_id = call.data.get(target["id_field"])
        if not item_id:
            return

        raw_note = _notes_data(hass, note_type).get(item_id, "")
        note, _updated_at = _note_text_and_updated(raw_note)
        hass.bus.async_fire(target["get_response_event"], {
            target["id_field"]: item_id,
            "note": note,
        })

    async def handle_delete_note_service(call, note_type):
        """Delete a note for an entity or device."""
        target = _note_target(note_type)
        item_id = call.data.get(target["id_field"])
        if not item_id:
            return

        await _delete_note(hass, note_type, item_id)

    async def handle_list_notes_service(call, note_type):
        """List all notes for a note type."""
        target = _note_target(note_type)
        hass.bus.async_fire(target["list_response_event"], {
            "notes": dict(_notes_data(hass, note_type)),
        })

    async def set_note_service(call):
        """Set a note for an entity."""
        await handle_set_note_service(call, "entity")

    async def get_note_service(call):
        """Get a note for an entity."""
        await handle_get_note_service(call, "entity")

    async def delete_note_service(call):
        """Delete a note for an entity."""
        await handle_delete_note_service(call, "entity")

    async def list_notes_service(call):
        """List all entity notes."""
        await handle_list_notes_service(call, "entity")

    async def backup_notes_service(call):
        """Backup all notes to a file."""
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        backup_path = hass.config.path("entity_notes_backup.json")

        try:
            # Use async_add_executor_job to avoid blocking the event loop
            def write_backup():
                with open(backup_path, "w") as f:
                    json.dump({
                        "entity_notes": entity_notes_data,
                        "device_notes": device_notes_data
                    }, f, indent=2)

            await hass.async_add_executor_job(write_backup)
            _LOGGER.info("Notes backed up to %s", backup_path)
        except Exception as e:
            _LOGGER.error("Failed to backup notes: %s", e)

    async def restore_notes_service(call):
        """Restore notes from a backup file."""
        backup_path = hass.config.path("entity_notes_backup.json")

        try:
            # Use async_add_executor_job to avoid blocking the event loop
            def read_backup():
                with open(backup_path, "r") as f:
                    return json.load(f)

            backup_data = await hass.async_add_executor_job(read_backup)

            store = hass.data[DOMAIN]["store"]

            # Handle both old and new backup formats
            if "entity_notes" in backup_data:
                hass.data[DOMAIN]["entity_notes"].update(backup_data.get("entity_notes", {}))
                hass.data[DOMAIN]["device_notes"].update(backup_data.get("device_notes", {}))
            else:
                # Old format - assume all are entity notes
                hass.data[DOMAIN]["entity_notes"].update(backup_data)

            await store.async_save({
                "entity_notes": hass.data[DOMAIN]["entity_notes"],
                "device_notes": hass.data[DOMAIN]["device_notes"]
            })
            _LOGGER.info("Notes restored from %s", backup_path)
        except Exception as e:
            _LOGGER.error("Failed to restore notes: %s", e)

    async def set_device_note_service(call):
        """Set a note for a device."""
        await handle_set_note_service(call, "device")

    async def get_device_note_service(call):
        """Get a note for a device."""
        await handle_get_note_service(call, "device")

    async def delete_device_note_service(call):
        """Delete a note for a device."""
        await handle_delete_note_service(call, "device")

    async def list_device_notes_service(call):
        """List all device notes."""
        await handle_list_notes_service(call, "device")

    # Register entity services
    hass.services.async_register(DOMAIN, SERVICE_SET_NOTE, set_note_service)
    hass.services.async_register(DOMAIN, SERVICE_GET_NOTE, get_note_service)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_NOTE, delete_note_service)
    hass.services.async_register(DOMAIN, SERVICE_LIST_NOTES, list_notes_service)
    hass.services.async_register(DOMAIN, SERVICE_BACKUP_NOTES, backup_notes_service)
    hass.services.async_register(DOMAIN, SERVICE_RESTORE_NOTES, restore_notes_service)

    # Register device services
    hass.services.async_register(DOMAIN, SERVICE_SET_DEVICE_NOTE, set_device_note_service)
    hass.services.async_register(DOMAIN, SERVICE_GET_DEVICE_NOTE, get_device_note_service)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_DEVICE_NOTE, delete_device_note_service)
    hass.services.async_register(DOMAIN, SERVICE_LIST_DEVICE_NOTES, list_device_notes_service)


class NotesView(HomeAssistantView):
    """Shared API handling for entity and device notes."""

    requires_auth = True
    note_type = None

    async def _get(self, request, item_id):
        """Get a note."""
        hass = request.app["hass"]
        raw_note = _notes_data(hass, self.note_type).get(item_id, "")
        note_text, updated_at = _note_text_and_updated(raw_note)

        user_name = request.query.get("user") or (
            request.get("hass_user").name if request.get("hass_user") else "User"
        )
        rendered_note = _render_note(hass, self.note_type, item_id, note_text, user_name)

        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]
        if debug_logging:
            _LOGGER.debug(
                "Retrieved note for %s: %s",
                _note_log_target(self.note_type, item_id),
                note_text[:50] + "..." if len(note_text) > 50 else note_text,
            )

        return web.json_response({
            "note": note_text,
            "rendered_note": rendered_note,
            "updated_at": updated_at,
        })

    async def _post(self, request, item_id):
        """Save a note."""
        hass = request.app["hass"]

        try:
            data = await request.json()
            note, updated_at = await _set_note(
                hass,
                self.note_type,
                item_id,
                data.get("note", ""),
                log_changes=False,
            )
            user_name = data.get("user_name") or (
                request.get("hass_user").name if request.get("hass_user") else "User"
            )
            rendered_note = _render_note(hass, self.note_type, item_id, note, user_name)

            return web.json_response({
                "status": "success",
                "updated_at": updated_at,
                "rendered_note": rendered_note,
            })

        except Exception as e:
            _LOGGER.error("Error saving note for %s: %s", _note_log_target(self.note_type, item_id), e)
            return web.json_response({"error": str(e)}, status=500)

    async def _delete(self, request, item_id):
        """Delete a note."""
        hass = request.app["hass"]

        try:
            if await _delete_note(hass, self.note_type, item_id, log_changes=False):
                return web.json_response({"status": "deleted"})
            return web.json_response({"status": "not_found"}, status=404)

        except Exception as e:
            _LOGGER.error("Error deleting note for %s: %s", _note_log_target(self.note_type, item_id), e)
            return web.json_response({"error": str(e)}, status=500)


class EntityNotesView(NotesView):
    """Handle Entity Notes API requests."""

    url = "/api/entity_notes/{entity_id}"
    name = "api:entity_notes"
    note_type = "entity"

    async def get(self, request, entity_id):
        """Get note for an entity."""
        return await self._get(request, entity_id)

    async def post(self, request, entity_id):
        """Save note for an entity."""
        return await self._post(request, entity_id)

    async def delete(self, request, entity_id):
        """Delete note for an entity."""
        return await self._delete(request, entity_id)


class DeviceNotesView(NotesView):
    """Handle Device Notes API requests."""

    url = "/api/device_notes/{device_id}"
    name = "api:device_notes"
    note_type = "device"

    async def get(self, request, device_id):
        """Get note for a device."""
        return await self._get(request, device_id)

    async def post(self, request, device_id):
        """Save note for a device."""
        return await self._post(request, device_id)

    async def delete(self, request, device_id):
        """Delete note for a device."""
        return await self._delete(request, device_id)


class EntityNotesRenderView(HomeAssistantView):
    """Handle rendering Jinja2 templates for Live Preview."""

    url = "/api/entity_notes/render"
    name = "api:entity_notes_render"
    requires_auth = True

    async def post(self, request):
        """Render a template."""
        hass = request.app["hass"]
        try:
            data = await request.json()
            note = data.get("note", "")
            entity_id = data.get("entity_id")
            device_id = data.get("device_id")

            rendered_note = note
            if note:
                try:
                    from homeassistant.helpers.template import Template
                    tpl = Template(note, hass)
                    user_name = data.get("user_name") or (request.get("hass_user").name if request.get("hass_user") else "User")
                    variables = {"user": user_name}
                    if entity_id:
                        variables["entity_id"] = entity_id
                    if device_id:
                        variables["device_id"] = device_id
                    rendered_note = str(tpl.async_render(variables, parse_result=False))
                except Exception as e:
                    _LOGGER.debug("Failed to render template during live preview: %s", e)
                    rendered_note = note

            return web.json_response({"rendered_note": rendered_note})

        except Exception as e:
            _LOGGER.error("Error rendering live preview: %s", e)
            return web.json_response({"rendered_note": data.get("note", "") if "data" in locals() else ""}, status=500)


class EntityNotesJSView(HomeAssistantView):
    """Serve the Entity Notes JavaScript file."""

    url = "/api/entity_notes/entity-notes.js"
    name = "api:entity_notes_js"
    requires_auth = False

    async def get(self, request):
        """Serve the JavaScript file."""
        hass = request.app["hass"]
        debug_logging = hass.data[DOMAIN]["config"].get(CONF_DEBUG_LOGGING, False)
        max_note_length = hass.data[DOMAIN]["config"].get(CONF_MAX_NOTE_LENGTH, 200)
        hide_buttons_when_empty = hass.data[DOMAIN]["config"].get(CONF_HIDE_BUTTONS_WHEN_EMPTY, False)
        hide_buttons_until_focus = hass.data[DOMAIN]["config"].get(CONF_HIDE_BUTTONS_UNTIL_FOCUS, False)
        enable_device_notes = hass.data[DOMAIN]["config"].get(CONF_ENABLE_DEVICE_NOTES, True)
        hide_markdown_toolbar = hass.data[DOMAIN]["config"].get(CONF_HIDE_MARKDOWN_TOOLBAR, DEFAULT_HIDE_MARKDOWN_TOOLBAR)
        show_markdown_toolbar = not hide_markdown_toolbar
        confirm_delete = hass.data[DOMAIN]["config"].get(CONF_CONFIRM_DELETE, True)
        hide_preview_button = hass.data[DOMAIN]["config"].get(CONF_HIDE_PREVIEW_BUTTON, False)
        hide_markdown_hints = hass.data[DOMAIN]["config"].get(CONF_HIDE_MARKDOWN_HINTS, False)
        empty_note_placeholder = hass.data[DOMAIN]["config"].get(CONF_EMPTY_NOTE_PLACEHOLDER, "")
        hide_last_modified = hass.data[DOMAIN]["config"].get(CONF_HIDE_LAST_MODIFIED, False)

        # Get the JavaScript file path
        js_file_path = Path(__file__).parent / FRONTEND_JS_PATH

        try:
            # Use async_add_executor_job to avoid blocking the event loop
            def read_file():
                with open(js_file_path, 'r') as f:
                    return f.read()

            js_content = await hass.async_add_executor_job(read_file)

            # Replace configuration placeholders
            js_content = js_content.replace('{{DEBUG_LOGGING}}', str(debug_logging).lower())
            js_content = js_content.replace('{{MAX_NOTE_LENGTH}}', str(max_note_length))
            js_content = js_content.replace('{{HIDE_BUTTONS_WHEN_EMPTY}}', str(hide_buttons_when_empty).lower())
            js_content = js_content.replace('{{HIDE_BUTTONS_UNTIL_FOCUS}}', str(hide_buttons_until_focus).lower())
            js_content = js_content.replace('{{ENABLE_DEVICE_NOTES}}', str(enable_device_notes).lower())
            js_content = js_content.replace('{{CONFIRM_DELETE}}', str(confirm_delete).lower())
            js_content = js_content.replace('{{SHOW_MARKDOWN_TOOLBAR}}', str(show_markdown_toolbar).lower())
            js_content = js_content.replace('{{HIDE_PREVIEW_BUTTON}}', str(hide_preview_button).lower())
            js_content = js_content.replace('{{HIDE_MARKDOWN_HINTS}}', str(hide_markdown_hints).lower())
            js_content = js_content.replace('{{EMPTY_NOTE_PLACEHOLDER}}', json.dumps(empty_note_placeholder))
            js_content = js_content.replace('{{HIDE_LAST_MODIFIED}}', str(hide_last_modified).lower())

            return web.Response(
                text=js_content,
                content_type='application/javascript',
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )

        except FileNotFoundError:
            _LOGGER.error("JavaScript file not found: %s", js_file_path)
            return web.Response(text="// Entity Notes: JavaScript file not found", content_type='application/javascript', status=404)
        except Exception as e:
            _LOGGER.error("Error serving JavaScript file: %s", e)
            return web.Response(text="// Entity Notes: Error loading script", content_type='application/javascript', status=500)
