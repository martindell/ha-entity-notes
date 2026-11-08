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
    CONF_HIDE_BUTTONS_WHEN_EMPTY,
    CONF_HIDE_BUTTONS_UNTIL_FOCUS,
    CONF_HIDE_CHAR_COUNT_UNTIL_FOCUS,
    CONF_DELETE_NOTES_WITH_ENTITY,
    CONF_DELETE_NOTES_WITH_DEVICE,
    CONF_ENABLE_DEVICE_NOTES,
    CONF_HIDE_MARKDOWN_TOOLBAR,
    CONF_SHOW_MARKDOWN_TOOLBAR,
    CONF_HIDE_MARKDOWN_PLACEHOLDER,
    CONF_CONFIRM_DELETE,
    CONF_HIDE_PREVIEW_BUTTON,
    CONF_HIDE_MARKDOWN_HINTS,
    CONF_EMPTY_NOTE_PLACEHOLDER,
    CONF_HIDE_LAST_MODIFIED,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_MAX_NOTE_LENGTH,
    DEFAULT_HIDE_BUTTONS_WHEN_EMPTY,
    DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS,
    DEFAULT_HIDE_CHAR_COUNT_UNTIL_FOCUS,
    DEFAULT_DELETE_NOTES_WITH_ENTITY,
    DEFAULT_DELETE_NOTES_WITH_DEVICE,
    DEFAULT_ENABLE_DEVICE_NOTES,
    DEFAULT_HIDE_MARKDOWN_TOOLBAR,
    DEFAULT_SHOW_MARKDOWN_TOOLBAR,
    DEFAULT_HIDE_MARKDOWN_PLACEHOLDER,
    DEFAULT_CONFIRM_DELETE,
    DEFAULT_HIDE_PREVIEW_BUTTON,
    DEFAULT_HIDE_MARKDOWN_HINTS,
    DEFAULT_EMPTY_NOTE_PLACEHOLDER,
    DEFAULT_HIDE_LAST_MODIFIED,
)

_LOGGER = logging.getLogger(__name__)

SECTION_DISPLAY = "display"
SECTION_BEHAVIOUR = "behaviour"
SECTION_ADVANCED = "advanced"

# Options grouped by section: (section_key, [(conf_key, default, validator), ...])
SECTION_CONFIG = [
    (SECTION_DISPLAY, [
        (CONF_HIDE_MARKDOWN_TOOLBAR, DEFAULT_HIDE_MARKDOWN_TOOLBAR, bool),
        (CONF_HIDE_MARKDOWN_PLACEHOLDER, DEFAULT_HIDE_MARKDOWN_PLACEHOLDER, bool),
        (CONF_HIDE_PREVIEW_BUTTON, DEFAULT_HIDE_PREVIEW_BUTTON, bool),
        (CONF_HIDE_MARKDOWN_HINTS, DEFAULT_HIDE_MARKDOWN_HINTS, bool),
        (CONF_EMPTY_NOTE_PLACEHOLDER, DEFAULT_EMPTY_NOTE_PLACEHOLDER, vol.All(str, vol.Length(max=120))),
        (CONF_HIDE_LAST_MODIFIED, DEFAULT_HIDE_LAST_MODIFIED, bool),
    ]),
    (SECTION_BEHAVIOUR, [
        (CONF_HIDE_BUTTONS_WHEN_EMPTY, DEFAULT_HIDE_BUTTONS_WHEN_EMPTY, bool),
        (CONF_HIDE_BUTTONS_UNTIL_FOCUS, DEFAULT_HIDE_BUTTONS_UNTIL_FOCUS, bool),
        (CONF_HIDE_CHAR_COUNT_UNTIL_FOCUS, DEFAULT_HIDE_CHAR_COUNT_UNTIL_FOCUS, bool),
        (CONF_CONFIRM_DELETE, DEFAULT_CONFIRM_DELETE, bool),
        (CONF_DELETE_NOTES_WITH_ENTITY, DEFAULT_DELETE_NOTES_WITH_ENTITY, bool),
        (CONF_DELETE_NOTES_WITH_DEVICE, DEFAULT_DELETE_NOTES_WITH_DEVICE, bool),
    ]),
    (SECTION_ADVANCED, [
        (CONF_ENABLE_DEVICE_NOTES, DEFAULT_ENABLE_DEVICE_NOTES, bool),
        (CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING, bool),
        (CONF_MAX_NOTE_LENGTH, DEFAULT_MAX_NOTE_LENGTH, vol.All(int, vol.Range(min=50, max=2000))),
    ]),
]

# Flat list derived from sections — used by normalize_options
CONFIG_OPTIONS = [opt for _, opts in SECTION_CONFIG for opt in opts]


def option_default(key: str, default: Any, current_options: dict[str, Any]) -> Any:
    """Return the form default, including legacy option fallbacks."""
    if key == CONF_HIDE_MARKDOWN_TOOLBAR and key not in current_options:
        return not current_options.get(CONF_SHOW_MARKDOWN_TOOLBAR, DEFAULT_SHOW_MARKDOWN_TOOLBAR)
    return current_options.get(key, default)


def build_options_schema(current_options: dict[str, Any] | None = None) -> vol.Schema:
    """Build the shared options schema with collapsible sections."""
    current_options = current_options or {}
    schema_dict = {}
    for section_key, opts in SECTION_CONFIG:
        section_options = {}
        for key, default, validator in opts:
            schema_key = vol.Optional(key, default=option_default(key, default, current_options))
            if key == CONF_EMPTY_NOTE_PLACEHOLDER:
                schema_key = vol.Optional(
                    key,
                    description={
                        "suggested_value": option_default(key, default, current_options)
                    },
                )
            section_options[schema_key] = validator
        section_schema = vol.Schema(section_options)
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


def normalize_options(
    user_input: dict[str, Any], current_options: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Flatten nested section structure into a flat options dict with defaults filled in."""
    current_options = current_options or {}
    flat: dict[str, Any] = {}
    for section_key, opts in SECTION_CONFIG:
        section_data = user_input.get(section_key, user_input)
        for key, default, _ in opts:
            if key in (CONF_ENABLE_DEVICE_NOTES, CONF_DELETE_NOTES_WITH_DEVICE):
                default = current_options.get(key, default)
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

        # Never replace an existing entry: its ID owns the dashboard sensor.
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            errors = validate_options(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Entity Notes",
                    data={},
                    options=normalize_options(user_input),
                )

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
                self.hass.config_entries.async_update_entry(
                    entry, data={}, options=normalize_options(user_input, entry.options)
                )
                return self.async_abort(reason="reconfigure_successful")

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
                    data=normalize_options(user_input, self.config_entry.options)
                )

                # The entry update listener reloads after HA commits these options.
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
