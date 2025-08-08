
"""The Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN, SERVICE_ADD_NOTE, SERVICE_REMOVE_NOTE, SERVICE_GET_NOTES

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Service schemas
ADD_NOTE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("note"): cv.string,
    vol.Optional("title"): cv.string,
})

REMOVE_NOTE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("note_id"): cv.string,
})

GET_NOTES_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_NOTE,
        _handle_add_note,
        schema=ADD_NOTE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_NOTE,
        _handle_remove_note,
        schema=REMOVE_NOTE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NOTES,
        _handle_get_notes,
        schema=GET_NOTES_SCHEMA,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _handle_add_note(call: ServiceCall) -> None:
    """Handle the add note service call."""
    entity_id = call.data["entity_id"]
    note = call.data["note"]
    title = call.data.get("title", "")
    
    _LOGGER.info("Adding note to entity %s: %s", entity_id, note)
    # Implementation would store the note associated with the entity


def _handle_remove_note(call: ServiceCall) -> None:
    """Handle the remove note service call."""
    entity_id = call.data["entity_id"]
    note_id = call.data.get("note_id")
    
    _LOGGER.info("Removing note from entity %s", entity_id)
    # Implementation would remove the note from the entity


def _handle_get_notes(call: ServiceCall) -> None:
    """Handle the get notes service call."""
    entity_id = call.data["entity_id"]
    
    _LOGGER.info("Getting notes for entity %s", entity_id)
    # Implementation would retrieve and return notes for the entity
