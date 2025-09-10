from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

DOMAIN = "entity_notes"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from YAML (not used, but keep for safety)."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    # Nothing to initialize yet; we just keep a placeholder for future state.
    hass.data[DOMAIN][entry.entry_id] = {}
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # If you add platforms later, forward unload here.
    # For now, just clean up our stored state.
    domain_data = hass.data.get(DOMAIN, {})
    domain_data.pop(entry.entry_id, None)
    # If empty, drop the domain bucket to keep memory tidy.
    if not domain_data:
        hass.data.pop(DOMAIN, None)
    return True
