"""Config flow for Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Module-level debug log to see if this file is being loaded
_LOGGER.warning("🔧 DEBUG: config_flow.py module loaded for domain: %s", DOMAIN)


class EntityNotesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Notes."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        _LOGGER.warning("🔧 DEBUG: EntityNotesConfigFlow.__init__ called")
        super().__init__()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.warning("🔧 DEBUG: async_step_user called with user_input: %s", user_input)
        
        # Check if already configured first
        existing_entries = self._async_current_entries()
        _LOGGER.warning("🔧 DEBUG: Found %d existing entries: %s", len(existing_entries), [e.title for e in existing_entries])
        
        if existing_entries:
            _LOGGER.warning("🔧 DEBUG: Integration already configured, aborting")
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            _LOGGER.warning("🔧 DEBUG: User input received, creating config entry")
            # Set unique ID but don't abort if already configured
            # This allows for proper cleanup and reinstallation
            await self.async_set_unique_id(DOMAIN)
            _LOGGER.warning("🔧 DEBUG: Unique ID set to: %s", DOMAIN)
            
            try:
                result = self.async_create_entry(
                    title="Entity Notes",
                    data={},
                )
                _LOGGER.warning("🔧 DEBUG: Config entry created successfully: %s", result)
                return result
            except Exception as e:
                _LOGGER.error("🔧 DEBUG: Failed to create config entry: %s", e)
                import traceback
                _LOGGER.error("🔧 DEBUG: Full traceback: %s", traceback.format_exc())
                raise

        _LOGGER.warning("🔧 DEBUG: Showing config form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "Entity Notes allows you to add custom notes to any Home Assistant entity. Notes will appear in the entity's more-info dialog."
            },
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        _LOGGER.warning("🔧 DEBUG: async_step_import called with import_info: %s", import_info)
        result = await self.async_step_user(import_info)
        _LOGGER.warning("🔧 DEBUG: async_step_import result: %s", result)
        return result


    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data={},
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "Reconfigure Entity Notes integration."
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EntityNotesOptionsFlow:
        """Get the options flow for this handler."""
        return EntityNotesOptionsFlow(config_entry)


class EntityNotesOptionsFlow(config_entries.OptionsFlow):
    """Handle Entity Notes options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "Configure Entity Notes options."
            },
        )

