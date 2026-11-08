"""Exercise the integration with real HA services, storage and HTTP responses."""
import asyncio
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError

from custom_components.entity_notes import (
    EntityNotesStore, EntityNotesView, DeviceNotesView, EntityNotesRenderView,
    async_register_services,
)
import custom_components.entity_notes as integration
from custom_components.entity_notes.config_flow import (
    build_options_schema, normalize_options, EntityNotesOptionsFlow,
)

class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.store = EntityNotesStore(self.hass, 2, 'entity_notes.notes')
        self.hass.data['entity_notes'] = {
            'store': self.store, 'write_lock': asyncio.Lock(),
            'entity_notes': {'sensor.test': 'original'}, 'device_notes': {'device1': 'original'},
            'config': {'max_note_length': 200, 'debug_logging': False},
        }
        await async_register_services(self.hass)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    async def call(self, name, data=None):
        await self.hass.services.async_call('entity_notes', name, data or {}, blocking=True)

    def request(self, data):
        class Request(dict):
            app = {'hass': self.hass}
            async def json(self):
                return data
        return Request()

    async def test_config_schema_builds_on_supported_ha(self):
        schema = build_options_schema()
        values = schema({'display': {}, 'behaviour': {}, 'advanced': {}})
        self.assertEqual(values['advanced']['max_note_length'], 200)

    async def test_store_roundtrip(self):
        await self.store.async_save({'entity_notes': {'sensor.test': 'saved'}, 'device_notes': {}})
        disk = json.loads((Path(self.temp.name) / '.storage/entity_notes.notes').read_text())
        self.assertEqual(disk['data']['entity_notes']['sensor.test'], 'saved')

    async def test_real_store_surfaces_write_error(self):
        with patch.object(Store, '_async_write_data', new=AsyncMock(side_effect=WriteError('disk full'))):
            with self.assertRaises(WriteError):
                await self.store.async_save({'entity_notes': {}, 'device_notes': {}})

    async def test_service_schemas_reject_missing_or_invalid_fields(self):
        for suffix, field, item_id in [('_note', 'entity_id', 'sensor.test'), ('_device_note', 'device_id', 'device1')]:
            for payload in [{field: item_id}, {field: item_id, 'note': None}, {field: item_id, 'note': 0}, {'note': 'text'}, {field: [], 'note': 'text'}]:
                with self.subTest(payload=payload), self.assertRaises((vol.Invalid, HomeAssistantError)):
                    await self.call('set' + suffix, payload)
            for action in ('get', 'delete'):
                with self.assertRaises((vol.Invalid, HomeAssistantError)):
                    await self.call(action + suffix, {})
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')
        self.assertEqual(self.hass.data['entity_notes']['device_notes']['device1'], 'original')

    async def test_rest_rejects_malformed_payload_without_mutation(self):
        for view, item_id in [(EntityNotesView(), 'sensor.test'), (DeviceNotesView(), 'device1')]:
            for payload in [{}, [], None, 'text', {'note': None}, {'note': False}, {'note': 123}, {'note': []}, {'note': 'changed', 'user_name': []}]:
                with self.subTest(payload=payload):
                    response = await view._post(self.request(payload), item_id)
                    self.assertEqual(response.status, 400)
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')
        self.assertEqual(self.hass.data['entity_notes']['device_notes']['device1'], 'original')

    async def test_explicit_empty_note_still_clears(self):
        response = await EntityNotesView()._post(self.request({'note': ''}), 'sensor.test')
        self.assertEqual(response.status, 200)
        self.assertNotIn('sensor.test', self.hass.data['entity_notes']['entity_notes'])
        await self.call('set_device_note', {'device_id': 'device1', 'note': ''})
        self.assertNotIn('device1', self.hass.data['entity_notes']['device_notes'])

    async def test_preview_rejects_invalid_body(self):
        for payload in [None, [], {}, {'note': 4}, {'note': 'x'*201}, {'note': 'text', 'entity_id': []}]:
            response = await EntityNotesRenderView().post(self.request(payload))
            self.assertEqual(response.status, 400)

    async def test_missing_and_malformed_restore_raise(self):
        with self.assertRaises(HomeAssistantError):
            await self.call('restore_notes')
        path = Path(self.temp.name) / 'entity_notes_backup.json'
        path.write_text('{bad JSON')
        with self.assertRaises(HomeAssistantError):
            await self.call('restore_notes')
        path.write_text(json.dumps({'entity_notes': {'sensor.test': 'changed'}, 'device_notes': {'bad': 42}}))
        with self.assertRaises(HomeAssistantError):
            await self.call('restore_notes')
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')

    async def test_backup_write_failure_raises(self):
        with patch('custom_components.entity_notes.atomic_write_json', side_effect=OSError('disk full')):
            with self.assertRaises(HomeAssistantError):
                await self.call('backup_notes')

    async def test_backup_restore_roundtrip(self):
        await self.call('backup_notes')
        await self.call('set_note', {'entity_id': 'sensor.test', 'note': 'changed'})
        await self.call('restore_notes')
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')

    async def test_restore_disk_failure_preserves_live_notes(self):
        path = Path(self.temp.name) / 'entity_notes_backup.json'
        path.write_text(json.dumps({'sensor.test': 'restored'}))
        with patch.object(Store, '_async_write_data', new=AsyncMock(side_effect=WriteError('disk full'))):
            with self.assertRaises(HomeAssistantError):
                await self.call('restore_notes')
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')

    async def test_rest_rejects_invalid_target(self):
        for method in ('_get', '_post', '_delete'):
            for item_id in ('invalid', '', 'sensor.test/other'):
                response = await getattr(EntityNotesView(), method)(self.request({'note': 'changed'}), item_id)
                self.assertEqual(response.status, 400)
        self.assertEqual(self.hass.data['entity_notes']['entity_notes']['sensor.test'], 'original')

    async def test_device_preferences_survive_options_save(self):
        existing = {'enable_device_notes': False, 'delete_notes_with_device': False}
        form_data = build_options_schema(existing)({'display': {'hide_last_modified': True},
                                                   'behaviour': {}, 'advanced': {}})
        with patch.object(EntityNotesOptionsFlow, 'config_entry', new_callable=PropertyMock) as entry:
            entry.return_value = type('Entry', (), {'options': existing})()
            result = await EntityNotesOptionsFlow().async_step_init(form_data)
        self.assertFalse(result['data']['enable_device_notes'])
        self.assertFalse(result['data']['delete_notes_with_device'])
        self.assertTrue(result['data']['hide_last_modified'])

    async def test_device_preferences_defaults_and_explicit_changes(self):
        existing = {'enable_device_notes': False, 'delete_notes_with_device': False}
        preserved = normalize_options({'display': {}, 'behaviour': {}, 'advanced': {}}, existing)
        self.assertFalse(preserved['enable_device_notes'])
        self.assertFalse(preserved['delete_notes_with_device'])
        changed = normalize_options({'advanced': {'enable_device_notes': True},
                                     'behaviour': {'delete_notes_with_device': True}}, existing)
        self.assertTrue(changed['enable_device_notes'])
        self.assertTrue(changed['delete_notes_with_device'])
        fresh = normalize_options({})
        self.assertTrue(fresh['enable_device_notes'])
        self.assertTrue(fresh['delete_notes_with_device'])

    async def test_debug_toggle_restores_previous_level(self):
        logger = logging.getLogger('entity_notes_test_debug')
        for initial in (logging.NOTSET, logging.WARNING, logging.DEBUG):
            logger.setLevel(initial)
            with patch.object(integration, '_LOGGER', logger), patch.object(integration, '_DEBUG_PREVIOUS_LEVEL', None):
                integration._configure_debug_logging(True)
                integration._configure_debug_logging(True)
                self.assertEqual(logger.level, logging.DEBUG)
                integration._configure_debug_logging(False)
                self.assertEqual(logger.level, initial)
                integration._configure_debug_logging(False)
                self.assertEqual(logger.level, initial)

    async def test_debug_toggle_respects_new_external_level(self):
        logger = logging.getLogger('entity_notes_test_external')
        logger.setLevel(logging.WARNING)
        with patch.object(integration, '_LOGGER', logger), patch.object(integration, '_DEBUG_PREVIOUS_LEVEL', None):
            integration._configure_debug_logging(True)
            logger.setLevel(logging.ERROR)
            integration._configure_debug_logging(False)
            self.assertEqual(logger.level, logging.ERROR)

    async def test_unload_restores_logger_level(self):
        logger = logging.getLogger('entity_notes_test_unload')
        logger.setLevel(logging.WARNING)
        with patch.object(integration, '_LOGGER', logger), patch.object(integration, '_DEBUG_PREVIOUS_LEVEL', None):
            integration._configure_debug_logging(True)
            self.assertTrue(await integration.async_unload_entry(self.hass, None))
            self.assertEqual(logger.level, logging.WARNING)
