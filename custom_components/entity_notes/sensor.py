"""Expose saved notes to dashboard templates."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from . import _note_text_and_updated
from .const import DOMAIN, EVENT_STORAGE_UPDATED


async def async_setup_entry(hass, entry, async_add_entities):
    """Add one sensor containing both entity and device notes."""
    async_add_entities([EntityNotesSensor(entry)])


class EntityNotesSensor(SensorEntity):
    """A count of saved notes with their raw text available as attributes."""

    _attr_name = "Entity Notes"
    _attr_icon = "mdi:note-text"
    _attr_should_poll = False
    _unrecorded_attributes = frozenset({"entity_notes", "device_notes"})

    def __init__(self, entry):
        self._attr_unique_id = f"{entry.entry_id}_notes"

    @property
    def native_value(self):
        """Return the total number of stored entity and device notes."""
        data = self.hass.data[DOMAIN]
        return len(data["entity_notes"]) + len(data["device_notes"])

    @property
    def extra_state_attributes(self):
        """Return fresh mappings without timestamps or template evaluation."""
        data = self.hass.data[DOMAIN]
        return {
            key: {item_id: _note_text_and_updated(note)[0]
                  for item_id, note in data[key].items()}
            for key in ("entity_notes", "device_notes")
        }

    async def async_added_to_hass(self):
        """Refresh only after persisted notes change; unsubscribe on removal."""
        await super().async_added_to_hass()

        @callback
        def notes_updated(event):
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_STORAGE_UPDATED, notes_updated)
        )
