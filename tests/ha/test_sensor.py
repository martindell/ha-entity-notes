"""Dashboard notes exercised through real HA platform setup and templates."""
import asyncio
import inspect
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntry, ConfigEntries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component

from custom_components.entity_notes import _set_note
from custom_components.entity_notes.const import EVENT_STORAGE_UPDATED


class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / 'custom_components').symlink_to(Path(__file__).resolve().parents[2] / 'custom_components')
        (root / '.storage').mkdir()
        (root / '.storage/entity_notes.notes').write_text(json.dumps({
            'version': 2, 'minor_version': 1, 'key': 'entity_notes.notes',
            'data': {'entity_notes': {'sensor.battery': 'Legacy note'},
                     'device_notes': {'device1': {'text': '**Charged**', 'updated_at': 1}}},
        }))
        self.hass = HomeAssistant(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addAsyncCleanup(self.hass.async_stop)
        self.hass.config.components.add("http")
        self.hass.http = Mock()
        loader.async_setup(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await er.async_load(self.hass)
        await dr.async_load(self.hass)
        entry_options = {}
        if "subentries_data" in inspect.signature(ConfigEntry).parameters:
            entry_options["subentries_data"] = []
        self.entry = ConfigEntry(
            version=1, minor_version=1, domain='entity_notes', title='Entity Notes',
            data={}, options={}, source='user', unique_id='entity_notes',
            discovery_keys=MappingProxyType({}), **entry_options,
        )
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        # HTTP/frontend registration is unrelated to the sensor. Keep real
        # config-entry and sensor-platform lifecycles, storage and event bus.
        self.http_patch = patch('custom_components.entity_notes.add_extra_js_url')
        self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.assertTrue(await async_setup_component(self.hass, 'entity_notes', {}))
        await self.hass.async_block_till_done()

    async def call(self, service, data=None):
        await self.hass.services.async_call('entity_notes', service, data or {}, blocking=True)
        await self.hass.async_block_till_done()

    def state(self):
        state = self.hass.states.get('sensor.entity_notes')
        self.assertIsNotNone(state)
        return state

    async def test_initial_attributes_and_literal_template_text(self):
        self.assertEqual(self.state().state, '2')
        self.assertEqual(self.state().attributes['entity_notes'], {'sensor.battery': 'Legacy note'})
        self.assertEqual(self.state().attributes['device_notes'], {'device1': '**Charged**'})
        note = "Battery {{ states('sensor.battery') }}%"
        await self.call('set_note', {'entity_id': 'sensor.battery', 'note': note})
        template = Template("{{ (state_attr('sensor.entity_notes', 'entity_notes') or {}).get('sensor.battery', '') }}", self.hass)
        self.assertEqual(template.async_render(parse_result=False), note)
        missing = Template("{{ (state_attr('sensor.entity_notes', 'entity_notes') or {}).get('sensor.missing', '') }}", self.hass)
        self.assertEqual(missing.async_render(parse_result=False), '')

    async def test_save_delete_clear_restore_and_failed_save(self):
        await self.call('backup_notes')
        old_state = self.state()
        await self.call('set_note', {'entity_id': 'sensor.battery', 'note': 'New text'})
        self.assertEqual(self.state().state, '2')
        self.assertEqual(self.state().attributes['entity_notes']['sensor.battery'], 'New text')
        self.assertEqual(old_state.attributes['entity_notes']['sensor.battery'], 'Legacy note')
        await self.call('delete_device_note', {'device_id': 'device1'})
        self.assertEqual(self.state().state, '1')
        self.assertEqual(self.state().attributes['device_notes'], {})
        await self.call('set_note', {'entity_id': 'sensor.battery', 'note': ''})
        self.assertEqual(self.state().state, '0')
        await self.call('restore_notes')
        self.assertEqual(self.state().state, '2')
        before = self.state()
        store = self.hass.data['entity_notes']['store']
        with patch.object(store, 'async_save', new=AsyncMock(side_effect=OSError('disk full'))):
            with self.assertRaises(OSError):
                await self.call('set_note', {'entity_id': 'sensor.battery', 'note': 'Not saved'})
        await self.hass.async_block_till_done()
        self.assertIs(self.state(), before)

    async def test_registry_rename_removal_and_reload(self):
        registry = er.async_get(self.hass)
        entity = registry.async_get_or_create('sensor', 'test', 'battery', suggested_object_id='battery')
        registry.async_update_entity(entity.entity_id, new_entity_id='sensor.renamed')
        await self.hass.async_block_till_done()
        self.assertEqual(self.state().attributes['entity_notes'], {'sensor.renamed': 'Legacy note'})
        registry.async_remove('sensor.renamed')
        await self.hass.async_block_till_done()
        self.assertEqual(self.state().attributes['entity_notes'], {})
        self.assertEqual(self.state().state, '1')
        self.assertTrue(await self.hass.config_entries.async_reload(self.entry.entry_id))
        await self.hass.async_block_till_done()
        self.assertEqual(self.state().attributes['device_notes']['device1'], '**Charged**')
        self.assertEqual(self.hass.bus.async_listeners().get(EVENT_STORAGE_UPDATED), 1)
        self.assertTrue(await self.hass.config_entries.async_unload(self.entry.entry_id))
        await self.hass.async_block_till_done()
        self.assertNotIn(EVENT_STORAGE_UPDATED, self.hass.bus.async_listeners())
        self.assertEqual(self.state().state, 'unavailable')

    async def test_device_updates_and_registry_removal(self):
        device = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id, identifiers={('entity_notes', 'test-device')},
        )
        er.async_get(self.hass).async_get_or_create(
            'sensor', 'test', 'device-battery', suggested_object_id='device_battery',
            device_id=device.id,
        )
        await self.call('set_device_note', {'device_id': device.id, 'note': 'Charged today'})
        template = Template("{{ (state_attr('sensor.entity_notes', 'device_notes') or {}).get(device_id('sensor.device_battery'), '') }}", self.hass)
        self.assertEqual(template.async_render(parse_result=False), 'Charged today')
        self.assertEqual(self.state().state, '3')
        dr.async_get(self.hass).async_remove_device(device.id)
        await self.hass.async_block_till_done()
        self.assertNotIn(device.id, self.state().attributes['device_notes'])
        self.assertEqual(self.state().state, '2')

    async def test_failed_platform_unload_keeps_sensor_and_services(self):
        with patch.object(self.hass.config_entries, 'async_unload_platforms',
                          new=AsyncMock(return_value=False)):
            self.assertFalse(await self.hass.config_entries.async_unload(self.entry.entry_id))
        self.assertEqual(self.state().state, '2')
        await self.call('set_note', {'entity_id': 'sensor.battery', 'note': 'Still running'})
        self.assertEqual(self.state().attributes['entity_notes']['sensor.battery'], 'Still running')

    async def test_note_attributes_excluded_from_recording(self):
        info = self.hass.states.get('sensor.entity_notes').state_info
        self.assertTrue({'entity_notes', 'device_notes'} <= info['unrecorded_attributes'])

    async def test_reload_drains_save_and_rejects_queued_and_new_writes(self):
        store = self.hass.data['entity_notes']['store']
        old_data = self.hass.data['entity_notes']
        started, release = asyncio.Event(), asyncio.Event()
        original_write = store._async_write_data

        async def delayed_write(*args, **kwargs):
            started.set()
            await release.wait()
            await original_write(*args, **kwargs)

        async def wait_for_unload():
            while not old_data.get('unloading'):
                await asyncio.sleep(0)

        with patch.object(store, '_async_write_data', delayed_write):
            saving = asyncio.create_task(_set_note(self.hass, 'entity', 'sensor.battery', 'Saved during reload'))
            await asyncio.wait_for(started.wait(), 2)
            queued = asyncio.create_task(_set_note(self.hass, 'entity', 'sensor.queued', 'Must retry'))
            await asyncio.sleep(0)
            reloading = asyncio.create_task(self.hass.config_entries.async_reload(self.entry.entry_id))
            try:
                await asyncio.wait_for(wait_for_unload(), 2)
                self.assertFalse(reloading.done())
                with self.assertRaises(HomeAssistantError):
                    await _set_note(self.hass, 'entity', 'sensor.new', 'Must retry')
            finally:
                release.set()
            await saving
            with self.assertRaises(HomeAssistantError):
                await queued
            self.assertTrue(await asyncio.wait_for(reloading, 2))
        await self.hass.async_block_till_done()
        self.assertEqual(self.state().attributes['entity_notes']['sensor.battery'], 'Saved during reload')
        await self.call('set_note', {'entity_id': 'sensor.other', 'note': 'Unrelated save'})
        disk = json.loads((Path(self.temp.name) / '.storage/entity_notes.notes').read_text())
        self.assertEqual(disk['data']['entity_notes']['sensor.battery']['text'], 'Saved during reload')
        self.assertNotIn('sensor.queued', disk['data']['entity_notes'])
        self.assertNotIn('sensor.new', disk['data']['entity_notes'])

    async def test_duplicate_setup_preserves_sensor_identity(self):
        registry = er.async_get(self.hass)
        before = registry.async_get('sensor.entity_notes')
        registry.async_update_entity('sensor.entity_notes', new_entity_id='sensor.my_notes')
        await self.hass.async_block_till_done()
        for source, data in [('user', None), ('import', {})]:
            result = await self.hass.config_entries.flow.async_init(
                'entity_notes', context={'source': source}, data=data,
            )
            self.assertEqual(result['type'], 'abort')
            self.assertEqual(result['reason'], 'already_configured')
        self.assertIs(self.hass.config_entries.async_get_entry(self.entry.entry_id), self.entry)
        self.assertEqual(registry.async_get('sensor.my_notes').unique_id, before.unique_id)
        self.assertIsNotNone(self.hass.states.get('sensor.my_notes'))
        self.assertIsNone(registry.async_get('sensor.entity_notes'))

    async def test_device_cleanup_independent_of_editor_visibility(self):
        for delete_notes in (True, False):
            device = dr.async_get(self.hass).async_get_or_create(
                config_entry_id=self.entry.entry_id,
                identifiers={('entity_notes', f'hidden-editor-{delete_notes}')},
            )
            await self.call('set_device_note', {'device_id': device.id, 'note': 'Hidden editor note'})
            self.hass.config_entries.async_update_entry(self.entry, options={
                'enable_device_notes': False, 'delete_notes_with_device': delete_notes,
            })
            await self.hass.async_block_till_done()
            dr.async_get(self.hass).async_remove_device(device.id)
            await self.hass.async_block_till_done()
            self.assertEqual(device.id in self.state().attributes['device_notes'], not delete_notes)
