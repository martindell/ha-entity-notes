"""Lightweight regression tests for storage and HA-facing callbacks.

HA infrastructure is represented by small fakes; production functions are loaded
from their AST so these tests do not require a full Home Assistant installation.
"""
import ast
import asyncio
from copy import deepcopy
import importlib.util
import json
import logging
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
import voluptuous as vol
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/entity_notes'
spec = importlib.util.spec_from_file_location('storage_utils', ROOT / 'storage_utils.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
validation_spec = importlib.util.spec_from_file_location('validation', ROOT / 'validation.py')
validation = importlib.util.module_from_spec(validation_spec)
validation_spec.loader.exec_module(validation)
TREE = ast.parse((ROOT / '__init__.py').read_text())
ENV = {'HomeAssistant': object, 'deepcopy': deepcopy, 'time': time,
       '_LOGGER': logging.getLogger('tests'), 'validate_notes': storage.validate_notes,
       'atomic_write_json': storage.atomic_write_json, 'json': json, 'vol': vol,
       'HomeAssistantError': RuntimeError, 'ServiceValidationError': ValueError,
       'validate_target': validation.validate_target,
       'validate_note_payload': validation.validate_note_payload}
exec((ROOT / 'const.py').read_text(), ENV)
functions = [n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name not in ('async_setup', 'async_setup_entry', 'async_unload_entry')]
functions += [n for n in TREE.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'NOTE_TARGETS' for t in n.targets)]
exec(compile(ast.Module(body=functions, type_ignores=[]), str(ROOT / '__init__.py'), 'exec'), ENV)

class Store:
    fail = False
    saved = None
    async def async_save(self, data):
        await asyncio.sleep(0)
        if self.fail:
            raise OSError('disk full')
        self.saved = deepcopy(data)

class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = Store()
        self.events = []
        self.data = {'store': self.store, 'write_lock': asyncio.Lock(),
                     'entity_notes': {'sensor.test': 'original'}, 'device_notes': {},
                     'config': {'max_note_length': 200, 'debug_logging': False}}
        self.hass = NS(data={'entity_notes': self.data},
                       bus=NS(async_fire=lambda *args: self.events.append(args)))

    async def test_failed_save_and_later_write_preserve_original(self):
        self.store.fail = True
        with self.assertRaises(OSError):
            await ENV['_set_note'](self.hass, 'entity', 'sensor.test', 'failed')
        self.assertEqual(self.data['entity_notes']['sensor.test'], 'original')
        self.assertEqual(self.events, [])
        self.store.fail = False
        await ENV['_set_note'](self.hass, 'device', 'device1', 'other')
        self.assertEqual(self.store.saved['entity_notes']['sensor.test'], 'original')

    async def test_failed_delete_preserves_note(self):
        self.store.fail = True
        with self.assertRaises(OSError):
            await ENV['_delete_note'](self.hass, 'entity', 'sensor.test')
        self.assertEqual(self.data['entity_notes']['sensor.test'], 'original')
        self.assertEqual(self.events, [])

    async def test_concurrent_entity_and_device_writes_survive(self):
        await asyncio.gather(
            ENV['_set_note'](self.hass, 'entity', 'sensor.test', 'new'),
            ENV['_set_note'](self.hass, 'device', 'device1', 'device'))
        self.assertEqual(self.store.saved['entity_notes']['sensor.test']['text'], 'new')
        self.assertEqual(self.store.saved['device_notes']['device1']['text'], 'device')

    async def test_oversized_note_rejected_without_mutation(self):
        with self.assertRaisesRegex(ValueError, 'maximum length'):
            await ENV['_set_note'](self.hass, 'entity', 'sensor.test', 'x' * 201)
        self.assertEqual(self.data['entity_notes']['sensor.test'], 'original')
        self.assertIsNone(self.store.saved)

    async def test_registry_disable_rename_and_remove(self):
        setup = next(n for n in TREE.body if getattr(n, 'name', None) == 'async_setup_entry')
        listener = next(n for n in ast.walk(setup) if getattr(n, 'name', None) == 'entity_registry_listener')
        env = dict(ENV, hass=self.hass, delete_notes_with_entity=True)
        exec(compile(ast.Module(body=[listener], type_ignores=[]), '<listener>', 'exec'), env)
        callback = env['entity_registry_listener']
        await callback(NS(data={'action': 'update', 'entity_id': 'sensor.test', 'changes': {'disabled_by': None}}))
        self.assertIn('sensor.test', self.data['entity_notes'])
        await callback(NS(data={'action': 'update', 'entity_id': 'sensor.renamed', 'changes': {'entity_id': 'sensor.test'}}))
        self.assertEqual(self.data['entity_notes'], {'sensor.renamed': 'original'})
        await callback(NS(data={'action': 'remove', 'entity_id': 'sensor.renamed'}))
        self.assertEqual(self.data['entity_notes'], {})
        source = (ROOT / '__init__.py').read_text()
        self.assertNotIn('async_listen("state_changed"', source)

    async def test_invalid_restore_is_all_or_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'entity_notes_backup.json'
            path.write_text(json.dumps({'entity_notes': {'sensor.test': 'replacement'}, 'device_notes': {'bad': 42}}))
            services = {}
            self.hass.config = NS(path=lambda name: str(Path(directory) / name))
            self.hass.services = NS(async_register=lambda domain, name, handler, **kwargs: services.update({name: handler}))
            async def executor(fn, *args):
                return fn(*args)
            self.hass.async_add_executor_job = executor
            await ENV['async_register_services'](self.hass)
            with self.assertRaisesRegex(RuntimeError, 'Failed to restore'):
                await services['restore_notes'](NS(data={}))
            self.assertEqual(self.data['entity_notes'], {'sensor.test': 'original'})
            self.assertIsNone(self.store.saved)

class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_propagates_errors_swallowed_by_base_store(self):
        class LoggingStore:
            async def async_save(self, data):
                try:
                    await self._async_write_data(data)
                except OSError:
                    pass  # Home Assistant logs these instead of raising.
            async def _async_write_data(self, data):
                raise OSError("disk full")
        node = next(n for n in TREE.body if getattr(n, 'name', None) == 'EntityNotesStore')
        env = {'Store': LoggingStore}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<store>', 'exec'), env)
        with self.assertRaisesRegex(OSError, 'disk full'):
            await env['EntityNotesStore']().async_save({})

    async def test_migration_aborts_when_backup_fails(self):
        setup = next(n for n in TREE.body if getattr(n, 'name', None) == 'async_setup_entry')
        with tempfile.TemporaryDirectory() as directory:
            storage_dir = Path(directory) / '.storage'
            storage_dir.mkdir()
            path = storage_dir / ENV['STORAGE_KEY']
            original = json.dumps({'version': 1, 'data': {'sensor.test': 'original'}})
            path.write_text(original)
            async def executor(fn, *args):
                return fn(*args)
            def failing_write(*args):
                raise OSError('backup failed')
            env = dict(ENV, ConfigEntry=object, Path=Path, atomic_write_json=failing_write)
            exec(compile(ast.Module(body=[setup], type_ignores=[]), '<setup>', 'exec'), env)
            hass = NS(config=NS(path=lambda name: str(Path(directory) / name)),
                      async_add_executor_job=executor)
            self.assertFalse(await env['async_setup_entry'](hass, NS(options={})))
            self.assertEqual(path.read_text(), original)

    async def test_options_step_does_not_reload_before_commit(self):
        tree = ast.parse((ROOT / 'config_flow.py').read_text())
        cls = next(n for n in tree.body if getattr(n, 'name', None) == 'EntityNotesOptionsFlow')
        method = next(n for n in cls.body if getattr(n, 'name', None) == 'async_step_init')
        method.returns = None
        for arg in method.args.args:
            arg.annotation = None
        env = {'validate_options': lambda data: {}, 'normalize_options': lambda data: data}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<options>', 'exec'), env)
        flow = NS(async_create_entry=lambda **kw: kw)
        result = await env['async_step_init'](flow, {'max_note_length': 300})
        self.assertEqual(result['data'], {'max_note_length': 300})


class StorageTests(unittest.TestCase):
    def test_valid_legacy_and_timestamped_notes(self):
        storage.validate_notes({'entity_notes': {'a': 'legacy', 'b': {'text': 'new', 'updated_at': 123}}})

    def test_invalid_shapes(self):
        for data in [[], {'entity_notes': []}, {'device_notes': {'x': 2}},
                     {'entity_notes': {'x': {'text': 'a', 'updated_at': 'bad'}}}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                storage.validate_notes(data)

    def test_failed_replace_preserves_original_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes'
            path.write_text('{"original": true}')
            with patch.object(storage.os, 'replace', side_effect=OSError('full')):
                with self.assertRaises(OSError):
                    storage.atomic_write_json(path, {'new': True})
            self.assertEqual(json.loads(path.read_text()), {'original': True})
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_atomic_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes'
            storage.atomic_write_json(path, {'text': 'café'})
            self.assertEqual(json.loads(path.read_text()), {'text': 'café'})

if __name__ == '__main__':
    unittest.main()
