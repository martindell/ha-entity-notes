"""Shared device-type notes: matching, lifecycle, persistence and API guards."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError

from custom_components.entity_notes import (
    DeviceTypeNotesView, EntityNotesStore, _set_note, _delete_note,
    async_register_services, device_type_identity,
)
from custom_components.entity_notes.config_flow import build_options_schema, normalize_options
from custom_components.entity_notes.const import STORAGE_VERSION


class DeviceTypeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.store = EntityNotesStore(self.hass, STORAGE_VERSION, 'entity_notes.notes')
        self.hass.data['entity_notes'] = {
            'store': self.store, 'write_lock': asyncio.Lock(),
            'entity_notes': {}, 'device_notes': {}, 'device_type_notes': {},
            'config': {'max_note_length': 200, 'debug_logging': False, 'enable_device_type_notes': True},
        }
        self.devices = {
            'one': SimpleNamespace(manufacturer='Acme', model='Switch 1'),
            'two': SimpleNamespace(manufacturer='Acme', model='Switch 1'),
            'other_model': SimpleNamespace(manufacturer='Acme', model='Switch 2'),
            'other_brand': SimpleNamespace(manufacturer='Other', model='Switch 1'),
            'unknown': SimpleNamespace(manufacturer=None, model=None),
        }
        self.registry = SimpleNamespace(devices=self.devices, async_get=self.devices.get)
        self.registry_patch = patch('homeassistant.helpers.device_registry.async_get', return_value=self.registry)
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)
        self.view = DeviceTypeNotesView()
        self.key = device_type_identity(self.devices['one'])
        await async_register_services(self.hass)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def request(self, method='GET', note='Hold button for 5 seconds', key=None):
        class Request(dict):
            app = {'hass': self.hass}
            query = {} if key is None else {'type_key': key}
            async def json(self):
                return {'note': note}
        request = Request()
        request.method = method
        return request

    async def get(self, device):
        response = await self.view.get(self.request(), device)
        self.assertEqual(response.status, 200)
        return json.loads(response.body)

    async def save(self, device='one', note='Hold button for 5 seconds'):
        return await self.view.post(self.request('POST', note, self.key), device)

    async def test_shared_note_matches_existing_and_future_devices(self):
        self.assertEqual((await self.save()).status, 200)
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')
        self.assertEqual((await self.get('two'))['device_count'], 2)
        self.devices['new'] = SimpleNamespace(manufacturer=' Acme ', model='SWITCH 1')
        self.assertEqual((await self.get('new'))['note'], 'Hold button for 5 seconds')
        self.assertEqual((await self.get('new'))['device_count'], 3)
        for device in ['other_model', 'other_brand']:
            self.assertEqual((await self.get(device))['note'], '')
        self.assertEqual(len(self.hass.data['entity_notes']['device_type_notes']), 1)

    async def test_individual_and_shared_notes_coexist_and_delete_independently(self):
        await _set_note(self.hass, 'device', 'one', 'Kitchen')
        await self.save()
        await _delete_note(self.hass, 'device', 'one')
        del self.devices['one']
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')
        await _set_note(self.hass, 'device', 'two', 'Hallway')
        response = await self.view.delete(self.request('DELETE', key=self.key), 'two')
        self.assertEqual(response.status, 200)
        self.assertEqual((await self.get('two'))['note'], '')
        self.assertEqual(self.hass.data['entity_notes']['device_notes']['two']['text'], 'Hallway')

    async def test_disabled_feature_blocks_all_endpoints_and_retains_notes(self):
        await self.save()
        self.hass.data['entity_notes']['config']['enable_device_type_notes'] = False
        for method in ['GET', 'POST', 'DELETE']:
            with self.subTest(method=method), self.assertRaises(web.HTTPForbidden):
                await getattr(self.view, method.lower())(self.request(method, key=self.key), 'one')
        # Ordinary saves must retain the hidden shared notes on disk.
        await _set_note(self.hass, 'entity', 'sensor.test', 'Individual')
        disk = json.loads((Path(self.temp.name) / '.storage/entity_notes.notes').read_text())
        self.assertIn(self.key, disk['data']['device_type_notes'])
        self.hass.data['entity_notes']['config']['enable_device_type_notes'] = True
        self.assertEqual((await self.get('one'))['note'], 'Hold button for 5 seconds')

    async def test_missing_metadata_does_not_group_unknown_devices(self):
        self.assertFalse((await self.get('unknown'))['supported'])
        self.assertEqual((await self.save('unknown')).status, 400)
        self.assertEqual(self.hass.data['entity_notes']['device_type_notes'], {})
        for manufacturer, model in [(None, 'x'), ('x', None), (' ', 'x'), ('x', ''), (4, 'x')]:
            self.assertIsNone(device_type_identity(SimpleNamespace(manufacturer=manufacturer, model=model)))

    async def test_missing_device_and_changed_type_reject_stale_edits(self):
        for method in ['GET', 'POST', 'DELETE']:
            with self.subTest(method=method), self.assertRaises(web.HTTPNotFound):
                await getattr(self.view, method.lower())(self.request(method, key=self.key), 'missing')
        await self.save()
        self.devices['one'].model = 'Switch 2'
        for method in ['POST', 'DELETE']:
            with self.assertRaises(web.HTTPConflict):
                await getattr(self.view, method.lower())(self.request(method, key=self.key), 'one')
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')
        self.assertEqual((await self.get('one'))['note'], '')

    async def test_shared_template_uses_viewed_device_context(self):
        await self.save(note='Device {{ device_id }}')
        self.assertEqual((await self.get('one'))['rendered_note'], 'Device one')
        self.assertEqual((await self.get('two'))['rendered_note'], 'Device two')

    async def test_write_failure_preserves_shared_note(self):
        await self.save()
        with patch.object(self.store, 'async_save', new=AsyncMock(side_effect=OSError('disk full'))):
            self.assertEqual((await self.save(note='Replacement')).status, 500)
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')

    async def test_backup_restore_includes_shared_notes_and_accepts_old_backups(self):
        await self.save()
        await self.hass.services.async_call('entity_notes', 'backup_notes', {}, blocking=True)
        path = Path(self.temp.name) / 'entity_notes_backup.json'
        self.assertIn(self.key, json.loads(path.read_text())['device_type_notes'])
        await self.save(note='Changed')
        await self.hass.services.async_call('entity_notes', 'restore_notes', {}, blocking=True)
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')
        path.write_text(json.dumps({'entity_notes': {'sensor.test': 'Old backup'}, 'device_notes': {}}))
        await self.hass.services.async_call('entity_notes', 'restore_notes', {}, blocking=True)
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')
        path.write_text(json.dumps({'device_type_notes': {self.key: 42}}))
        with self.assertRaises(HomeAssistantError):
            await self.hass.services.async_call('entity_notes', 'restore_notes', {}, blocking=True)
        self.assertEqual((await self.get('two'))['note'], 'Hold button for 5 seconds')

    async def test_v2_migrates_without_losing_notes(self):
        original = {'entity_notes': {'sensor.test': 'Old'}, 'device_notes': {'one': 'Kitchen'}}
        await Store(self.hass, 2, 'migration-test').async_save(original)
        migrated = await EntityNotesStore(self.hass, STORAGE_VERSION, 'migration-test').async_load()
        self.assertEqual(migrated, {**original, 'device_type_notes': {}})

    async def test_options_default_off_and_preserve_explicit_choice(self):
        defaults = build_options_schema()({'display': {}, 'behaviour': {}, 'advanced': {}})
        self.assertFalse(defaults['advanced']['enable_device_type_notes'])
        existing = {'enable_device_type_notes': True}
        self.assertTrue(normalize_options({}, existing)['enable_device_type_notes'])
        self.assertFalse(normalize_options({'advanced': {'enable_device_type_notes': False}}, existing)['enable_device_type_notes'])

    async def test_identity_has_no_separator_collisions(self):
        a = SimpleNamespace(manufacturer='a:b', model='c')
        b = SimpleNamespace(manufacturer='a', model='b:c')
        self.assertNotEqual(device_type_identity(a), device_type_identity(b))
