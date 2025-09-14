"""Config flow for Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

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
                        CONF_MAX_NOTE_LENGTH,
                        default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                    ): vol.All(int, vol.Range(min=50, max=2000)),
                    vol.Optional(
                        CONF_AUTO_BACKUP,
                        default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                    ): bool,
                    vol.Optional(
                        CONF_HIDE_BUTTONS_WHEN_EMPTY,
                        default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                    ): bool,
                }),
                errors=errors,
                description_placeholders={
                    "description": "⚠️ Entity Notes is already installed and will be automatically upgraded with your new settings. Your existing notes and data will be preserved during the upgrade process."
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
                            _LOGGER.debug(f"Removing existing entry: {entry.entry_id} (title: {entry.title})")
                            await self.hass.config_entries.async_remove(entry.entry_id)
                        
                        _LOGGER.info("Successfully removed existing Entity Notes entries")
                        
                    except Exception as ex:
                        _LOGGER.error(f"Error during Entity Notes upgrade: {ex}")
                        errors["base"] = "upgrade_failed"
                        return self.async_show_form(
                            step_id="user",
                            data_schema=vol.Schema({
                                vol.Optional(CONF_DEBUG_LOGGING, default=DEFAULT_DEBUG_LOGGING): bool,
                                vol.Optional(CONF_MAX_NOTE_LENGTH, default=DEFAULT_MAX_NOTE_LENGTH): vol.All(int, vol.Range(min=50, max=2000)),
                                vol.Optional(CONF_AUTO_BACKUP, default=DEFAULT_AUTO_BACKUP): bool,
                                vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=DEFAULT_HIDE_BUTTONS_WHEN_EMPTY): bool,
                            }),
                            errors=errors,
                            description_placeholders={
                                "description": "❌ Error during upgrade. Please try again or manually remove the existing Entity Notes integration first from Settings > Devices & Services."
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
                        CONF_MAX_NOTE_LENGTH: max_length,
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
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
                vol.Optional(CONF_MAX_NOTE_LENGTH, default=DEFAULT_MAX_NOTE_LENGTH): vol.All(int, vol.Range(min=50, max=2000)),
                vol.Optional(CONF_AUTO_BACKUP, default=DEFAULT_AUTO_BACKUP): bool,
                vol.Optional(CONF_HIDE_BUTTONS_WHEN_EMPTY, default=DEFAULT_HIDE_BUTTONS_WHEN_EMPTY): bool,
            }),
            errors=errors,
            description_placeholders={
                "description": "Entity Notes allows you to add custom notes to any Home Assistant entity. Configure your preferences below."
            },
        )

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_info)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self._get_reconfigure_entry()
        errors = {}
        
        if user_input is not None:
            # Validate input
            max_length = user_input.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
            if max_length < 50 or max_length > 2000:
                errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
            
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data={},
                    options={
                        CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
                        CONF_MAX_NOTE_LENGTH: max_length,
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
                    },
                    reason="reconfigure_successful",
                )

        current_options = entry.options or {}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEBUG_LOGGING,
                    default=current_options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
                ): bool,
                vol.Optional(
                    CONF_MAX_NOTE_LENGTH,
                    default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                ): vol.All(int, vol.Range(min=50, max=2000)),
                vol.Optional(
                    CONF_AUTO_BACKUP,
                    default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                ): bool,
                vol.Optional(
                    CONF_HIDE_BUTTONS_WHEN_EMPTY,
                    default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                ): bool,
            }),
            errors=errors,
            description_placeholders={
                "description": "Update your Entity Notes configuration settings."
            },
        )

    @staticmethod
    @callback
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
        errors = {}
        
        if user_input is not None:
            # Validate input
            max_length = user_input.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
            if max_length < 50 or max_length > 2000:
                errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
            
            if not errors:
                # Create the options entry first
                result = self.async_create_entry(
                    title="",
                    data={
                        CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING),
                        CONF_MAX_NOTE_LENGTH: max_length,
                        CONF_AUTO_BACKUP: user_input.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP),
                        CONF_HIDE_BUTTONS_WHEN_EMPTY: user_input.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY),
                    }
                )
                
                # Automatically reload the integration to apply the new settings
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                
                return result

        current_options = self.config_entry.options or {}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEBUG_LOGGING,
                    default=current_options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
                ): bool,
                vol.Optional(
                    CONF_MAX_NOTE_LENGTH,
                    default=current_options.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
                ): vol.All(int, vol.Range(min=50, max=2000)),
                vol.Optional(
                    CONF_AUTO_BACKUP,
                    default=current_options.get(CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP)
                ): bool,
                vol.Optional(
                    CONF_HIDE_BUTTONS_WHEN_EMPTY,
                    default=current_options.get(CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY)
                ): bool,
            }),
            errors=errors,
            description_placeholders={
                "description": "Configure Entity Notes behavior and settings."
            },
        )
