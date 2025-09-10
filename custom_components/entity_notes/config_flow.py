"""Config flow for Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_DEBUG_LOGGING,
    CONF_MAX_NOTE_LENGTH,
    CONF_AUTO_BACKUP,
    CONF_HIDE_BUTTONS_WHEN_EMPTY,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_AUTO_BACKUP,
    DEFAULT_HIDE_BUTTONS_WHEN_EMPTY,
)

_LOGGER = logging.getLogger(__name__)

# Define the schema - three checkboxes, then number input
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEBUG_LOGGING, default=DEFAULT_DEBUG_LOGGING): bool,
        vol.Optional(CONF_AUTO_BACKUP, default=DEFAULT_AUTO_BACKUP): bool,
        vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=DEFAULT_HIDE_BUTTONS_WHEN_EMPTY): bool,
        vol.Optional(CONF_MAX_NOTE_LENGTH, default=DEFAULT_MAX_NOTE_LENGTH): vol.All(
            vol.Coerce(int), vol.Range(min=50, max=2000)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input."""
    max_length = data.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
    if not isinstance(max_length, int) or max_length < 50 or max_length > 2000:
        raise InvalidMaxLength

    return {"title": "Entity Notes"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Notes."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidMaxLength:
                errors["base"] = "invalid_max_length"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors
        )

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Entity Notes config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        
        # Get current values from config entry
        current_debug = self.config_entry.data.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        current_auto_backup = self.config_entry.data.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
        current_hide_buttons = self.config_entry.data.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
        current_max_length = self.config_entry.data.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
        
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except InvalidMaxLength:
                errors["base"] = "invalid_max_length"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})

        # Create schema with current values as defaults - same order as initial setup
        options_schema = vol.Schema({
            vol.Optional(CONF_DEBUG_LOGGING, default=current_debug): bool,
            vol.Optional(CONF_AUTO_BACKUP, default=current_auto_backup): bool,
            vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=current_hide_buttons): bool,
            vol.Optional(CONF_MAX_NOTE_LENGTH, default=current_max_length): vol.All(
                vol.Coerce(int), vol.Range(min=50, max=2000)
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidMaxLength(HomeAssistantError):
    """Error to indicate the max length is invalid."""
