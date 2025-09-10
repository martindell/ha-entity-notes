"""Config flow for Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
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


class EntityNotesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Notes."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        # Check if already configured and handle automatic upgrade
        existing_entries = self._async_current_entries()
        if existing_entries and user_input is None:
            # Get current options from existing entry to pre-populate form
            current_options = existing_entries[0].options if existing_entries[0].options else {}
            
            # Show form with upgrade notice for first-time display
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(
                        CONF_DEBUG_LOGGING,
                        default=current_options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
                    ): bool,
                    vol.Optional(
                        CONF_HIDE_BUTTONS_WHEN_EMPTY,
                        default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                    ): bool,
                    vol.Optional(
                        CONF_AUTO_BACKUP,
                        default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                    ): bool,
                    vol.Optional(
                        CONF_MAX_NOTE_LENGTH,
                        default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                    ): vol.All(int, vol.Range(min=50, max=2000)),
                }),
                errors=errors,
                description_placeholders={
                    "description": "⚠️ Entity Notes is already installed and will be automatically upgraded with your current settings."
                },
            )

        if user_input is not None:
            # Validate input
            max_length = user_input.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
            if max_length < 50 or max_length > 2000:
                errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
            
            if not errors:
                # Handle automatic upgrade of existing installation
                if existing_entries:
                    try:
                        _LOGGER.info("Automatically upgrading existing Entity Notes installation")
                        
                        # Remove existing entries one by one
                        for entry in existing_entries:
                            _LOGGER.debug(f"Removing existing entry: {entry.entry_id} {title: {entry.title}}")
                            await self.hass.config_entries.async_remove(entry.entry_id)
                        
                        _LOGGER.info("Successfully removed existing Entity Notes entries")
                    
                    except Exception as ex:
                        _LOGGER.error(f"Error during Entity Notes upgrade: {ex}")
                        errors["base"] = "upgrade_failed"
                        return self.async_show_form(
                            step_id="user",
                            data_schema=vol.Schema({
                                vol.Optional(CONF_DEBUG_LOGGING, default=DEFAULT_DEBUG_LOGGING): bool,
                                vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=DEFAULT_HIDE_BUTTONS_WHEN_EMPTY): bool,
                                vol.Optional(CONF_AUTO_BACKUP, default=DEFAULT_AUTO_BACKUP): bool,
                                vol.Optional(CONF_MAX_NOTE_LENGTH, default=DEFAULT_MAX_NOTE_LENGTH): vol.All(int, vol.Range(min=50, max=2000)),
                            }),
                            errors=errors,
                            description_placeholders={
                                "description": "❌ Error during upgrade. Please try again or manually remove the existing integration."
                            },
                        )
                
                # Create new entry (either fresh install or after successful upgrade)
                await self.async_set_unique_id(DOMAIN)
                
                # Create the new entry with user's settings
                entry_result = self.async_create_entry(
                    title="Entity Notes",
                    data={},
                    options={
                        CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_MAX_NOTE_LENGTH: max_length,
                    },
                )
                
                if existing_entries:
                    _LOGGER.info("Entity Notes upgrade completed successfully")
                else:
                    _LOGGER.info("Entity Notes installation completed successfully")
                
                return entry_result

        # Show configuration form for fresh install
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_DEBUG_LOGGING, default=DEFAULT_DEBUG_LOGGING): bool,
                vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=DEFAULT_HIDE_BUTTONS_WHEN_EMPTY): bool,
                vol.Optional(CONF_AUTO_BACKUP, default=DEFAULT_AUTO_BACKUP): bool,
                vol.Optional(CONF_MAX_NOTE_LENGTH, default=DEFAULT_MAX_NOTE_LENGTH): vol.All(int, vol.Range(min=50, max=2000)),
            }),
            errors=errors,
            description_placeholders={
                "description": "Entity Notes allows you to add custom notes to any Home Assistant entity. Configure the behavior and settings below."
            },
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_info)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}
        
        if user_input is not None:
            # Validate input
            max_length = user_input.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
            if max_length < 50 or max_length > 2000:
                errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
            
            if not errors:
                # Update the entry with new options
                self.hass.config_entries.async_update_entry(
                    entry,
                    options={
                        CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_MAX_NOTE_LENGTH: max_length,
                    },
                )
                
                return self.async_create_entry(title="", data={})

        # Get current values
        current_options = entry.options if entry.options else {}
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEBUG_LOGGING,
                    default=current_options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
                ): bool,
                vol.Optional(
                    CONF_HIDE_BUTTONS_WHEN_EMPTY,
                    default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                ): bool,
                vol.Optional(
                    CONF_AUTO_BACKUP,
                    default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                ): bool,
                vol.Optional(
                    CONF_MAX_NOTE_LENGTH,
                    default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                ): vol.All(int, vol.Range(min=50, max=2000)),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return EntityNotesOptionsFlow(config_entry)


class EntityNotesOptionsFlow(config_entries.OptionsFlow):
    """Entity Notes config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # Validate input
            max_length = user_input.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
            if max_length < 50 or max_length > 2000:
                errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
            
            if not errors:
                # Create the options entry
                result = self.async_create_entry(
                    title="",
                    data={
                        CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_MAX_NOTE_LENGTH: max_length,
                    },
                )
                
                # Reload the integration to apply new settings immediately
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                
                return result

        # Get current values
        current_options = self.config_entry.options if self.config_entry.options else {}
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEBUG_LOGGING,
                    default=current_options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
                ): bool,
                vol.Optional(
                    CONF_HIDE_BUTTONS_WHEN_EMPTY,
                    default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                ): bool,
                vol.Optional(
                    CONF_AUTO_BACKUP,
                    default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                ): bool,
                vol.Optional(
                    CONF_MAX_NOTE_LENGTH,
                    default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                ): vol.All(int, vol.Range(min=50, max=2000)),
            }),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
