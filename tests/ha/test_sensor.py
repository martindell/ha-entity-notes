"""Dashboard notes exercised through real HA platform setup and templates."""
import inspect
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import loader
from homeassistant.config_entries import ConfigEntry, ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component

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
