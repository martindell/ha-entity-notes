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
    CONF_DELETE_NOTES_WITH_ENTITY,
    CONF_DELETE_NOTES_WITH_DEVICE,
    CONF_ENABLE_DEVICE_NOTES,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_AUTO_BACKUP,
    DEFAULT_HIDE_BUTTONS_WHEN_EMPTY,
    DEFAULT_DELETE_NOTES_WITH_ENTITY,
    DEFAULT_DELETE_NOTES_WITH_DEVICE,
    DEFAULT_ENABLE_DEVICE_NOTES,
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
    delete_notes_with_entity = options.get(CONF_DELETE_NOTES_WITH_ENTITY, DEFAULT_DELETE_NOTES_WITH_ENTITY)
    delete_notes_with_device = options.get(CONF_DELETE_NOTES_WITH_DEVICE, DEFAULT_DELETE_NOTES_WITH_DEVICE)
    enable_device_notes = options.get(CONF_ENABLE_DEVICE_NOTES, DEFAULT_ENABLE_DEVICE_NOTES)
    
    if debug_logging:
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug logging enabled for Entity Notes")
    
    try:
        # Initialize storage
        _LOGGER.debug("Initializing storage")
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        # Load existing notes
        try:
            stored_data = await store.async_load()
            _LOGGER.warning("=" * 80)
            _LOGGER.warning("ENTITY NOTES LOADING DEBUG")
            _LOGGER.warning("Store.async_load() returned: %s", "None" if stored_data is None else f"dict with {len(stored_data)} keys: {list(stored_data.keys())}")

            # Check if we need to manually load v1 data (Store returns None for version mismatches)
            if stored_data is None:
                _LOGGER.warning("Store returned None - checking for v1 data to migrate")
                storage_path = Path(hass.config.path(".storage")) / STORAGE_KEY
                _LOGGER.warning("Looking for storage file at: %s", storage_path)
                _LOGGER.warning("File exists: %s", storage_path.exists())

                if storage_path.exists():
                    try:
                        with open(storage_path, 'r') as f:
                            file_data = json.load(f)
                        file_version = file_data.get("version")
                        _LOGGER.warning("Found storage file with version: %s", file_version)

                        if file_version == 1:
                            _LOGGER.warning("Found v1 storage file, loading data for migration")
                            stored_data = file_data.get("data", {})
                            _LOGGER.warning("Loaded %d items from v1 file", len(stored_data))
                        else:
                            _LOGGER.warning("Storage file version is %s, not v1", file_version)
                    except Exception as e:
                        _LOGGER.error("Failed to manually load v1 data: %s", e)
                        import traceback
                        _LOGGER.error("Traceback: %s", traceback.format_exc())
            _LOGGER.warning("=" * 80)

            # Migrate from v1 to v2 storage format if needed
            if stored_data and "entity_notes" not in stored_data:
                # Old format detected: flat dictionary of entity_id: note
                _LOGGER.warning("=" * 80)
                _LOGGER.warning("MIGRATING Entity Notes from v1 to v2 format")
                _LOGGER.warning("Found %d entity notes to migrate", len(stored_data))

                # Create backup before migration
                try:
                    backup_path = Path(hass.config.path(".storage")) / "entity_notes.notes.backup_v1"
                    backup_data = {
                        "version": 1,
                        "minor_version": 1,
                        "key": STORAGE_KEY,
                        "data": stored_data
                    }
                    with open(backup_path, 'w') as f:
                        json.dump(backup_data, f, indent=2)
                    _LOGGER.warning("Created backup at: %s", backup_path)
                except Exception as backup_error:
                    _LOGGER.error("Failed to create backup before migration: %s", backup_error)
                    _LOGGER.error("Migration aborted for safety - please backup your data manually")
                    raise

                # Perform migration
                entity_notes_data = stored_data.copy()
                device_notes_data = {}

                # Save migrated data immediately
                try:
                    await store.async_save({
                        "entity_notes": entity_notes_data,
                        "device_notes": device_notes_data
                    })
                    _LOGGER.warning("Successfully migrated %d entity notes to v2 format", len(entity_notes_data))
                    _LOGGER.warning("Migration complete - backup saved as entity_notes.notes.backup_v1")
                    _LOGGER.warning("=" * 80)
                except Exception as save_error:
                    _LOGGER.error("Failed to save migrated data: %s", save_error)
                    _LOGGER.error("Your original data is safe in the backup file")
                    raise
            else:
                # New format: structured with entity_notes and device_notes
                entity_notes_data = stored_data.get("entity_notes", {}) if stored_data else {}
                device_notes_data = stored_data.get("device_notes", {}) if stored_data else {}

            _LOGGER.info("Loaded %d entity notes and %d device notes",
                         len(entity_notes_data), len(device_notes_data))
        except Exception as e:
            _LOGGER.warning("Could not load notes storage, starting fresh: %s", e)
            entity_notes_data = {}
            device_notes_data = {}

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
                CONF_DELETE_NOTES_WITH_ENTITY: delete_notes_with_entity,
                CONF_DELETE_NOTES_WITH_DEVICE: delete_notes_with_device,
                CONF_ENABLE_DEVICE_NOTES: enable_device_notes,
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


async def async_register_services(hass: HomeAssistant) -> None:
    """Register the Entity Notes services."""

    async def set_note_service(call):
        """Set a note for an entity."""
        entity_id = call.data.get("entity_id")
        note = call.data.get("note", "")

        if not entity_id:
            _LOGGER.error("No entity_id provided for set_note service")
            return

        store = hass.data[DOMAIN]["store"]
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]

        # Truncate note if too long
        if len(note) > max_length:
            note = note[:max_length]
            _LOGGER.warning("Note truncated to %d characters for %s", max_length, entity_id)

        if note.strip():
            entity_notes_data[entity_id] = note.strip()
            _LOGGER.info("Set note for %s", entity_id)
        else:
            entity_notes_data.pop(entity_id, None)
            _LOGGER.info("Removed note for %s", entity_id)

        await store.async_save({
            "entity_notes": entity_notes_data,
            "device_notes": hass.data[DOMAIN]["device_notes"]
        })
        hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": note})

    async def get_note_service(call):
        """Get a note for an entity."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            return

        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        note = entity_notes_data.get(entity_id, "")

        hass.bus.async_fire("entity_notes_get_response", {
            "entity_id": entity_id,
            "note": note
        })

    async def delete_note_service(call):
        """Delete a note for an entity."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            return

        store = hass.data[DOMAIN]["store"]
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]

        if entity_id in entity_notes_data:
            del entity_notes_data[entity_id]
            await store.async_save({
                "entity_notes": entity_notes_data,
                "device_notes": hass.data[DOMAIN]["device_notes"]
            })
            hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": ""})
            _LOGGER.info("Deleted note for %s", entity_id)

    async def list_notes_service(call):
        """List all entity notes."""
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        hass.bus.async_fire("entity_notes_list_response", {"notes": dict(entity_notes_data)})

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

    # Device note services
    async def set_device_note_service(call):
        """Set a note for a device."""
        device_id = call.data.get("device_id")
        note = call.data.get("note", "")

        if not device_id:
            _LOGGER.error("No device_id provided for set_device_note service")
            return

        store = hass.data[DOMAIN]["store"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]

        # Truncate note if too long
        if len(note) > max_length:
            note = note[:max_length]
            _LOGGER.warning("Note truncated to %d characters for device %s", max_length, device_id)

        if note.strip():
            device_notes_data[device_id] = note.strip()
            _LOGGER.info("Set note for device %s", device_id)
        else:
            device_notes_data.pop(device_id, None)
            _LOGGER.info("Removed note for device %s", device_id)

        await store.async_save({
            "entity_notes": hass.data[DOMAIN]["entity_notes"],
            "device_notes": device_notes_data
        })
        hass.bus.async_fire(EVENT_DEVICE_NOTES_UPDATED, {"device_id": device_id, "note": note})

    async def get_device_note_service(call):
        """Get a note for a device."""
        device_id = call.data.get("device_id")
        if not device_id:
            return

        device_notes_data = hass.data[DOMAIN]["device_notes"]
        note = device_notes_data.get(device_id, "")

        hass.bus.async_fire("device_notes_get_response", {
            "device_id": device_id,
            "note": note
        })

    async def delete_device_note_service(call):
        """Delete a note for a device."""
        device_id = call.data.get("device_id")
        if not device_id:
            return

        store = hass.data[DOMAIN]["store"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]

        if device_id in device_notes_data:
            del device_notes_data[device_id]
            await store.async_save({
                "entity_notes": hass.data[DOMAIN]["entity_notes"],
                "device_notes": device_notes_data
            })
            hass.bus.async_fire(EVENT_DEVICE_NOTES_UPDATED, {"device_id": device_id, "note": ""})
            _LOGGER.info("Deleted note for device %s", device_id)

    async def list_device_notes_service(call):
        """List all device notes."""
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        hass.bus.async_fire("device_notes_list_response", {"notes": dict(device_notes_data)})

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


class EntityNotesView(HomeAssistantView):
    """Handle Entity Notes API requests."""

    url = "/api/entity_notes/{entity_id}"
    name = "api:entity_notes"
    requires_auth = False  # Local requests only

    async def get(self, request, entity_id):
        """Get note for an entity."""
        hass = request.app["hass"]
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        note = entity_notes_data.get(entity_id, "")

        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]
        if debug_logging:
            _LOGGER.debug("Retrieved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)

        return web.json_response({"note": note})

    async def post(self, request, entity_id):
        """Save note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            data = await request.json()
            note = data.get("note", "").strip()

            # Enforce max length
            if len(note) > max_length:
                note = note[:max_length]

            if note:
                entity_notes_data[entity_id] = note
                if debug_logging:
                    _LOGGER.debug("Saved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
            else:
                # Remove empty notes
                entity_notes_data.pop(entity_id, None)
                if debug_logging:
                    _LOGGER.debug("Removed empty note for %s", entity_id)

            # Save to persistent storage
            await store.async_save({
                "entity_notes": entity_notes_data,
                "device_notes": hass.data[DOMAIN]["device_notes"]
            })

            # Fire event
            hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": note})

            return web.json_response({"status": "success"})

        except Exception as e:
            _LOGGER.error("Error saving note for %s: %s", entity_id, e)
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, entity_id):
        """Delete note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        entity_notes_data = hass.data[DOMAIN]["entity_notes"]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            if entity_id in entity_notes_data:
                del entity_notes_data[entity_id]
                if debug_logging:
                    _LOGGER.debug("Deleted note for %s", entity_id)

                # Save to persistent storage
                await store.async_save({
                    "entity_notes": entity_notes_data,
                    "device_notes": hass.data[DOMAIN]["device_notes"]
                })

                # Fire event
                hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": ""})

                return web.json_response({"status": "deleted"})
            else:
                return web.json_response({"status": "not_found"}, status=404)

        except Exception as e:
            _LOGGER.error("Error deleting note for %s: %s", entity_id, e)
            return web.json_response({"error": str(e)}, status=500)


class DeviceNotesView(HomeAssistantView):
    """Handle Device Notes API requests."""

    url = "/api/device_notes/{device_id}"
    name = "api:device_notes"
    requires_auth = False  # Local requests only

    async def get(self, request, device_id):
        """Get note for a device."""
        hass = request.app["hass"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        note = device_notes_data.get(device_id, "")

        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]
        if debug_logging:
            _LOGGER.debug("Retrieved note for device %s: %s", device_id, note[:50] + "..." if len(note) > 50 else note)

        return web.json_response({"note": note})

    async def post(self, request, device_id):
        """Save note for a device."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            data = await request.json()
            note = data.get("note", "").strip()

            # Enforce max length
            if len(note) > max_length:
                note = note[:max_length]

            if note:
                device_notes_data[device_id] = note
                if debug_logging:
                    _LOGGER.debug("Saved note for device %s: %s", device_id, note[:50] + "..." if len(note) > 50 else note)
            else:
                # Remove empty notes
                device_notes_data.pop(device_id, None)
                if debug_logging:
                    _LOGGER.debug("Removed empty note for device %s", device_id)

            # Save to persistent storage
            await store.async_save({
                "entity_notes": hass.data[DOMAIN]["entity_notes"],
                "device_notes": device_notes_data
            })

            # Fire event
            hass.bus.async_fire(EVENT_DEVICE_NOTES_UPDATED, {"device_id": device_id, "note": note})

            return web.json_response({"status": "success"})

        except Exception as e:
            _LOGGER.error("Error saving note for device %s: %s", device_id, e)
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, device_id):
        """Delete note for a device."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        device_notes_data = hass.data[DOMAIN]["device_notes"]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            if device_id in device_notes_data:
                del device_notes_data[device_id]
                if debug_logging:
                    _LOGGER.debug("Deleted note for device %s", device_id)

                # Save to persistent storage
                await store.async_save({
                    "entity_notes": hass.data[DOMAIN]["entity_notes"],
                    "device_notes": device_notes_data
                })

                # Fire event
                hass.bus.async_fire(EVENT_DEVICE_NOTES_UPDATED, {"device_id": device_id, "note": ""})

                return web.json_response({"status": "deleted"})
            else:
                return web.json_response({"status": "not_found"}, status=404)

        except Exception as e:
            _LOGGER.error("Error deleting note for device %s: %s", device_id, e)
            return web.json_response({"error": str(e)}, status=500)


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
        enable_device_notes = hass.data[DOMAIN]["config"].get(CONF_ENABLE_DEVICE_NOTES, True)

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
            js_content = js_content.replace('{{ENABLE_DEVICE_NOTES}}', str(enable_device_notes).lower())

            return web.Response(text=js_content, content_type='application/javascript')

        except FileNotFoundError:
            _LOGGER.error("JavaScript file not found: %s", js_file_path)
            return web.Response(text="// Entity Notes: JavaScript file not found", content_type='application/javascript', status=404)
        except Exception as e:
            _LOGGER.error("Error serving JavaScript file: %s", e)
            return web.Response(text="// Entity Notes: Error loading script", content_type='application/javascript', status=500)
