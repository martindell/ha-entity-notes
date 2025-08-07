"""Entity Notes integration for Home Assistant."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.storage import Store
from homeassistant.components.frontend import add_extra_js_url
from aiohttp import web
import json
import os

_LOGGER = logging.getLogger(__name__)

DOMAIN = "entity_notes"
STORAGE_VERSION = 1
STORAGE_KEY = "entity_notes.notes"

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Entity Notes integration from configuration.yaml."""
    # This is for backward compatibility with configuration.yaml
    # The main setup now happens in async_setup_entry
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    _LOGGER.info("Setting up Entity Notes integration")

    # Initialize storage
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    # Load existing notes
    try:
        stored_data = await store.async_load()
        notes_data = stored_data or {}
    except Exception as e:
        _LOGGER.warning("Could not load notes storage, starting fresh: %s", e)
        notes_data = {}

    # Store the storage instance and data in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "store": store,
        "notes": notes_data
    }

    # Register the API view
    hass.http.register_view(EntityNotesView())
    
    # Register the JavaScript file serving view
    hass.http.register_view(EntityNotesJSView())

    # Register frontend resource
    # Serve the JS file directly from the integration
    try:
        # Register the JS file served by our own endpoint
        add_extra_js_url(hass, "/api/entity_notes/entity-notes.js")
        _LOGGER.info("Registered frontend resource: /api/entity_notes/entity-notes.js")
            
    except Exception as e:
        _LOGGER.error("Failed to register frontend resource: %s", e)

    _LOGGER.info("Entity Notes integration setup complete")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Clean up if needed
    return True

class EntityNotesView(HomeAssistantView):
    """Handle Entity Notes API requests."""

    url = "/api/entity_notes/{entity_id}"
    name = "api:entity_notes"
    requires_auth = False  # Simplified - no auth required for local requests

    async def get(self, request, entity_id):
        """Get note for an entity."""
        hass = request.app["hass"]
        notes_data = hass.data[DOMAIN]["notes"]

        note = notes_data.get(entity_id, "")
        _LOGGER.debug("Retrieved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
        return web.json_response({"note": note})

    async def post(self, request, entity_id):
        """Save note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        notes_data = hass.data[DOMAIN]["notes"]

        try:
            data = await request.json()
            note = data.get("note", "").strip()

            if note:
                notes_data[entity_id] = note
                _LOGGER.info("Saved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
            else:
                # Remove empty notes
                notes_data.pop(entity_id, None)
                _LOGGER.info("Removed empty note for %s", entity_id)

            # Save to persistent storage
            await store.async_save(notes_data)

            return web.json_response({"status": "success"})

        except Exception as e:
            _LOGGER.error("Error saving note for %s: %s", entity_id, e)
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, entity_id):
        """Delete note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        notes_data = hass.data[DOMAIN]["notes"]

        try:
            if entity_id in notes_data:
                del notes_data[entity_id]
                _LOGGER.info("Deleted note for %s", entity_id)

                # Save to persistent storage
                await store.async_save(notes_data)

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
        try:
            # Get the path to the JavaScript file
            integration_dir = os.path.dirname(__file__)
            js_file_path = os.path.join(integration_dir, "..", "..", "www", "entity-notes.js")
            
            # Check if file exists
            if not os.path.exists(js_file_path):
                _LOGGER.error("JavaScript file not found at: %s", js_file_path)
                return web.Response(text="// JavaScript file not found", content_type="application/javascript", status=404)
            
            # Read and serve the file
            with open(js_file_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            _LOGGER.debug("Serving JavaScript file from: %s", js_file_path)
            return web.Response(text=js_content, content_type="application/javascript")
            
        except Exception as e:
            _LOGGER.error("Error serving JavaScript file: %s", e)
            return web.Response(text="// Error loading JavaScript file", content_type="application/javascript", status=500)

