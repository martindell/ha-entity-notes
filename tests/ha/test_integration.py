"""Exercise the integration with real HA services, storage and HTTP responses."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError

from custom_components.entity_notes import (
    EntityNotesStore, EntityNotesView, DeviceNotesView, EntityNotesRenderView,
    async_register_services,
)
from custom_components.entity_notes.config_flow import build_options_schema

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
