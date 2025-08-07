"""Entity Notes integration for Home Assistant."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
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
    """Set up the Entity Notes integration."""
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
    hass.data[DOMAIN] = {
        "store": store,
        "notes": notes_data
    }

    # Register the API view
    hass.http.register_view(EntityNotesView())

    # Register frontend resource
    # This automatically adds the JavaScript file to the frontend
    integration_dir = os.path.dirname(__file__)
    js_file = os.path.join(integration_dir, "..", "..", "www", "entity-notes.js")
    
    if os.path.exists(js_file):
        add_extra_js_url(hass, "/local/entity-notes.js")
        _LOGGER.info("Registered frontend resource: /local/entity-notes.js")
    else:
        _LOGGER.warning("Frontend resource not found: %s", js_file)

    _LOGGER.info("Entity Notes integration setup complete")
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