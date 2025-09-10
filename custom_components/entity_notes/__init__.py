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
from functools import partial

from .const import (
    DOMAIN,
    STORAGE_VERSION,
    STORAGE_KEY,
    MAX_NOTE_LENGTH,
    CONF_DEBUG_LOGGING,
    CONF_MAX_NOTE_LENGTH,
    CONF_AUTO_BACKUP,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_AUTO_BACKUP,
    FRONTEND_JS_PATH,
    EVENT_NOTES_UPDATED,
    SERVICE_SET_NOTE,
    SERVICE_GET_NOTE,
    SERVICE_DELETE_NOTE,
    SERVICE_LIST_NOTES,
    SERVICE_BACKUP_NOTES,
    SERVICE_RESTORE_NOTES,
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
            notes_data = stored_data or {}
            _LOGGER.debug("Loaded %d existing notes", len(notes_data))
        except Exception as e:
            _LOGGER.warning("Could not load notes storage, starting fresh: %s", e)
            notes_data = {}

        # Generate cache buster for JavaScript file
        cache_buster = int(time.time())

        # Store the configuration and data in hass.data
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN] = {
            "store": store,
            "notes": notes_data,
            "config": {
                CONF_DEBUG_LOGGING: debug_logging,
                CONF_MAX_NOTE_LENGTH: max_note_length,
                CONF_AUTO_BACKUP: auto_backup,
            },
            "entry_id": entry.entry_id,
            "cache_buster": cache_buster,
        }

        # Register the API view
        hass.http.register_view(EntityNotesView())
        _LOGGER.debug("EntityNotesView registered")
        
        # Register the JavaScript file serving view
        hass.http.register_view(EntityNotesJSView())
        _LOGGER.debug("EntityNotesJSView registered")

        # Register frontend resource with cache busting
        try:
            js_url_with_cache_buster = f"/api/entity_notes/entity-notes.js?v={cache_buster}"
            add_extra_js_url(hass, js_url_with_cache_buster)
            _LOGGER.debug("Frontend resource registered: %s", js_url_with_cache_buster)
        except Exception as e:
            _LOGGER.error("Failed to register frontend resource: %s", e)

        # Register services
        await async_register_services(hass)

        _LOGGER.info("Entity Notes integration setup completed successfully")
        return True
        
    except Exception as e:
        _LOGGER.error("Critical error in Entity Notes setup: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Entity Notes integration")
    
    try:
        # Remove services
        services_to_remove = [
            SERVICE_SET_NOTE,
            SERVICE_GET_NOTE,
            SERVICE_DELETE_NOTE,
            SERVICE_LIST_NOTES,
            SERVICE_BACKUP_NOTES,
            SERVICE_RESTORE_NOTES,
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
        notes_data = hass.data[DOMAIN]["notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]
        
        # Truncate note if too long
        if len(note) > max_length:
            note = note[:max_length]
            _LOGGER.warning("Note truncated to %d characters for %s", max_length, entity_id)
        
        if note.strip():
            notes_data[entity_id] = note.strip()
            _LOGGER.info("Set note for %s", entity_id)
        else:
            notes_data.pop(entity_id, None)
            _LOGGER.info("Removed note for %s", entity_id)
        
        await store.async_save(notes_data)
        hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": note})

    async def get_note_service(call):
        """Get a note for an entity."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            return
            
        notes_data = hass.data[DOMAIN]["notes"]
        note = notes_data.get(entity_id, "")
        
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
        notes_data = hass.data[DOMAIN]["notes"]
        
        if entity_id in notes_data:
            del notes_data[entity_id]
            await store.async_save(notes_data)
            hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": ""})
            _LOGGER.info("Deleted note for %s", entity_id)

    async def list_notes_service(call):
        """List all notes."""
        notes_data = hass.data[DOMAIN]["notes"]
        hass.bus.async_fire("entity_notes_list_response", {"notes": dict(notes_data)})

    async def backup_notes_service(call):
        """Backup all notes to a file."""
        notes_data = hass.data[DOMAIN]["notes"]
        backup_path = hass.config.path("entity_notes_backup.json")
        
        try:
            with open(backup_path, "w") as f:
                json.dump(notes_data, f, indent=2)
            _LOGGER.info("Notes backed up to %s", backup_path)
        except Exception as e:
            _LOGGER.error("Failed to backup notes: %s", e)

    async def restore_notes_service(call):
        """Restore notes from a backup file."""
        backup_path = hass.config.path("entity_notes_backup.json")
        
        try:
            with open(backup_path, "r") as f:
                backup_data = json.load(f)
            
            store = hass.data[DOMAIN]["store"]
            hass.data[DOMAIN]["notes"].update(backup_data)
            await store.async_save(hass.data[DOMAIN]["notes"])
            _LOGGER.info("Notes restored from %s", backup_path)
        except Exception as e:
            _LOGGER.error("Failed to restore notes: %s", e)

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_NOTE, set_note_service)
    hass.services.async_register(DOMAIN, SERVICE_GET_NOTE, get_note_service)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_NOTE, delete_note_service)
    hass.services.async_register(DOMAIN, SERVICE_LIST_NOTES, list_notes_service)
    hass.services.async_register(DOMAIN, SERVICE_BACKUP_NOTES, backup_notes_service)
    hass.services.async_register(DOMAIN, SERVICE_RESTORE_NOTES, restore_notes_service)


class EntityNotesView(HomeAssistantView):
    """Handle Entity Notes API requests."""

    url = "/api/entity_notes/{entity_id}"
    name = "api:entity_notes"
    requires_auth = False  # Local requests only

    async def get(self, request, entity_id):
        """Get note for an entity."""
        hass = request.app["hass"]
        notes_data = hass.data[DOMAIN]["notes"]
        note = notes_data.get(entity_id, "")
        
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]
        if debug_logging:
            _LOGGER.debug("Retrieved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
            
        return web.json_response({"note": note})

    async def post(self, request, entity_id):
        """Save note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        notes_data = hass.data[DOMAIN]["notes"]
        max_length = hass.data[DOMAIN]["config"][CONF_MAX_NOTE_LENGTH]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            data = await request.json()
            note = data.get("note", "").strip()

            # Enforce max length
            if len(note) > max_length:
                note = note[:max_length]

            if note:
                notes_data[entity_id] = note
                if debug_logging:
                    _LOGGER.debug("Saved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
            else:
                # Remove empty notes
                notes_data.pop(entity_id, None)
                if debug_logging:
                    _LOGGER.debug("Removed empty note for %s", entity_id)

            # Save to persistent storage
            await store.async_save(notes_data)
            
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
        notes_data = hass.data[DOMAIN]["notes"]
        debug_logging = hass.data[DOMAIN]["config"][CONF_DEBUG_LOGGING]

        try:
            if entity_id in notes_data:
                del notes_data[entity_id]
                if debug_logging:
                    _LOGGER.debug("Deleted note for %s", entity_id)

                # Save to persistent storage
                await store.async_save(notes_data)
                
                # Fire event
                hass.bus.async_fire(EVENT_NOTES_UPDATED, {"entity_id": entity_id, "note": ""})

                return web.json_response({"status": "deleted"})
            else:
                return web.json_response({"status": "not_found"}, status=404)

        except Exception as e:
            _LOGGER.error("Error deleting note for %s: %s", entity_id, e)
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
        
        # Get the JavaScript file path
        js_file_path = Path(__file__).parent / FRONTEND_JS_PATH
        
        try:
            # Async-safe file read to avoid blocking open()
            js_content = await hass.async_add_executor_job(
                partial(Path(js_file_path).read_text, encoding="utf-8")
            )

            # Replace configuration placeholders
            js_content = js_content.replace('{{DEBUG_LOGGING}}', str(debug_logging).lower())
            js_content = js_content.replace('{{MAX_NOTE_LENGTH}}', str(max_note_length))
                
            return web.Response(text=js_content, content_type='application/javascript')
            
        except FileNotFoundError:
            _LOGGER.error("JavaScript file not found: %s", js_file_path)
            return web.Response(text="// Entity Notes: JavaScript file not found", content_type='application/javascript', status=404)
        except Exception as e:
            _LOGGER.error("Error serving JavaScript file: %s", e)
            return web.Response(text="// Entity Notes: Error loading script", content_type='application/javascript', status=500)
