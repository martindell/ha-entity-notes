"""Config flow for Entity Notes integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult, section

from .const import (
    DOMAIN,
    CONF_DEBUG_LOGGING,
    CONF_MAX_NOTE_LENGTH,
    CONF_AUTO_BACKUP,
    CONF_HIDE_BUTTONS_WHEN_EMPTY,
    CONF_HIDE_BUTTONS_UNTIL_FOCUS,
    CONF_DELETE_NOTES_WITH_ENTITY,
    CONF_SHOW_MARKDOWN_TOOLBAR,
    CONF_CONFIRM_DELETE,
    CONF_HIDE_PREVIEW_BUTTON,
    CONF_HIDE_MARKDOWN_HINTS,
    CONF_HIDE_LAST_MODIFIED,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_AUTO_BACKUP,
    DEFAULT_HIDE_BUTTONS_WHEN_EMPTY,
    DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS,
    DEFAULT_DELETE_NOTES_WITH_ENTITY,
    DEFAULT_SHOW_MARKDOWN_TOOLBAR,
    DEFAULT_CONFIRM_DELETE,
    DEFAULT_HIDE_PREVIEW_BUTTON,
    DEFAULT_HIDE_MARKDOWN_HINTS,
    DEFAULT_HIDE_LAST_MODIFIED,
)

_LOGGER = logging.getLogger(__name__)

SECTION_DISPLAY = "display"
SECTION_BEHAVIOUR = "behaviour"
SECTION_ADVANCED = "advanced"

# Options grouped by section: (section_key, [(conf_key, default, validator), ...])
SECTION_CONFIG = [
    (SECTION_DISPLAY, [
        (CONF_SHOW_MARKDOWN_TOOLBAR, DEFAULT_SHOW_MARKDOWN_TOOLBAR, bool),
        (CONF_HIDE_PREVIEW_BUTTON, DEFAULT_HIDE_PREVIEW_BUTTON, bool),
        (CONF_HIDE_MARKDOWN_HINTS, DEFAULT_HIDE_MARKDOWN_HINTS, bool),
        (CONF_HIDE_LAST_MODIFIED, DEFAULT_HIDE_LAST_MODIFIED, bool),
    ]),
    (SECTION_BEHAVIOUR, [
        (CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY, bool),
        (CONF_HIDE_BUTTONS_UNTIL_FOCUS, DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS, bool),
        (CONF_CONFIRM_DELETE, DEFAULT_CONFIRM_DELETE, bool),
        (CONF_DELETE_NOTES_WITH_ENTITY, DEFAULT_DELETE_NOTES_WITH_ENTITY, bool),
    ]),
    (SECTION_ADVANCED, [
        (CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING, bool),
        (CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH, vol.All(int, vol.Range(min=50, max=2000))),
        (CONF_AUTO_BACKUP, DEFAULT_AUTO_BACKUP, bool),
    ]),
]

# Flat list derived from sections — used by normalize_options
CONFIG_OPTIONS = [opt for _, opts in SECTION_CONFIG for opt in opts]


def build_options_schema(current_options: dict[str, Any] | None = None) -> vol.Schema:
    """Build the shared options schema with collapsible sections."""
    current_options = current_options or {}
    schema_dict = {}
    for section_key, opts in SECTION_CONFIG:
        section_schema = vol.Schema({
            vol.Optional(key, default=current_options.get(key, default)): validator
            for key, default, validator in opts
        })
        schema_dict[vol.Required(section_key)] = section(section_schema, {"collapsed": True})
    return vol.Schema(schema_dict)


def validate_options(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate options entered by the user. user_input is nested (section keys → sub-dicts)."""
    errors = {}
    advanced_data = user_input.get(SECTION_ADVANCED, user_input)
    max_length = advanced_data.get(CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH)
    if max_length < 50 or max_length > 2000:
        errors[CONF_MAX_NOTE_LENGTH] = "invalid_max_length"
    return errors


def normalize_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested section structure into a flat options dict with defaults filled in."""
    flat: dict[str, Any] = {}
    for section_key, opts in SECTION_CONFIG:
        section_data = user_input.get(section_key, user_input)
        for key, default, _ in opts:
            flat[key] = section_data.get(key, default)
    return flat


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
                data_schema=build_options_schema(current_options),
                errors=errors,
                description_placeholders={
                    "description": "Entity Notes is already installed and will be automatically upgraded with your new settings. Your existing notes and data will be preserved during the upgrade process."
                },
            )

        if user_input is not None:
            errors = validate_options(user_input)

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
                            data_schema=build_options_schema(),
                            errors=errors,
                            description_placeholders={
                                "description": "Error during upgrade. Please try again or manually remove the existing Entity Notes integration first from Settings > Devices & Services."
                            },
                        )

                # Create new entry (either fresh install or after successful upgrade)
                await self.async_set_unique_id(DOMAIN)

                # Create the new entry with user's settings
                entry_result = self.async_create_entry(
                    title="Entity Notes",
                    data={},
                    options=normalize_options(user_input),
                )

                if existing_entries:
                    _LOGGER.info("Entity Notes upgrade completed successfully")
                else:
                    _LOGGER.info("Entity Notes installation completed successfully")

                return entry_result

        # Show configuration form for fresh install
        return self.async_show_form(
            step_id="user",
            data_schema=build_options_schema(),
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
            errors = validate_options(user_input)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data={},
                    options=normalize_options(user_input),
                    reason="reconfigure_successful",
                )

        current_options = entry.options or {}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=build_options_schema(current_options),
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
        return EntityNotesOptionsFlow()


class EntityNotesOptionsFlow(config_entries.OptionsFlow):
    """Handle Entity Notes options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            errors = validate_options(user_input)

            if not errors:
                # Create the options entry first
                result = self.async_create_entry(
                    title="",
                    data=normalize_options(user_input)
                )

                # Automatically reload the integration to apply the new settings
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return result

        current_options = self.config_entry.options or {}
        return self.async_show_form(
            step_id="init",
            data_schema=build_options_schema(current_options),
            errors=errors,
            description_placeholders={
                "description": "Configure Entity Notes behavior and settings."
            },
        )
