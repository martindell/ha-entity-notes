# Release Notes - Version 3.0.0

## 🎉 Major New Feature: Device Notes

You can now add notes to **devices** in addition to entities! Device notes work exactly like entity notes, appearing directly in the device settings dialog.

### What's New

- ✅ **Device Notes**: Add, edit, and delete notes for any device in Home Assistant
- ✅ **Automatic Migration**: Seamlessly upgrades your existing entity notes from v1 to v2 storage format
- ✅ **Automatic Backups**: Creates a backup of your data before migration
- ✅ **Improved UI Detection**: Enhanced detection for different Home Assistant dialog types

### New Services

Four new services for device notes:
- `entity_notes.set_device_note` - Add or update a note for a device
- `entity_notes.get_device_note` - Retrieve a device's note
- `entity_notes.delete_device_note` - Remove a device's note
- `entity_notes.list_device_notes` - List all device notes

## ⚠️ IMPORTANT: Backup Recommendation

**Before upgrading to v3.0.0, we recommend backing up your notes file as a precaution:**

```bash
cp /config/.storage/entity_notes.notes /config/.storage/entity_notes.notes.backup_manual
```

While the integration automatically creates a backup during migration, having your own backup provides extra safety.

## 🔄 Automatic Migration

This version includes an **automatic migration** from v1 to v2 storage format:

### What Happens During Migration

1. **Detection**: The integration detects if you're using v1 storage format
2. **Backup**: Automatically creates `/config/.storage/entity_notes.notes.backup_v1`
3. **Migration**: Converts your data to v2 format (adds support for device notes)
4. **Verification**: Logs confirm the number of notes migrated

### Migration Logs

When you restart Home Assistant after upgrading, you'll see:

```
================================================================================
MIGRATING Entity Notes from v1 to v2
Found storage version 1, upgrading to version 2
Found XX entity notes to migrate
Created backup at: /config/.storage/entity_notes.notes.backup_v1
Successfully migrated XX entity notes to v2
================================================================================
```

### If Something Goes Wrong

If you experience any issues:

1. Your backup is at: `/config/.storage/entity_notes.notes.backup_v1`
2. You can restore it by copying it back:
   ```bash
   cp /config/.storage/entity_notes.notes.backup_v1 /config/.storage/entity_notes.notes
   ```
3. Report the issue at: https://github.com/martindell/ha-entity-notes/issues

## 📝 Using Device Notes

### Via UI
1. Go to **Settings → Devices & Services**
2. Click on the **Devices** tab
3. Click on any device name
4. The notes field will appear in the device settings dialog

### Via Services
```yaml
# Add a note to a device
service: entity_notes.set_device_note
data:
  device_id: "abc123..."
  note: "This is my device note"
```

## 🔧 Configuration

Device notes are **enabled by default**. To disable them:

1. Go to **Settings → Devices & Services → Entity Notes**
2. Click **Configure**
3. Uncheck **Enable Device Notes**

## 📊 Storage Format Changes

### v1 Format (old):
```json
{
  "version": 1,
  "data": {
    "sensor.temperature": "My note"
  }
}
```

### v2 Format (new):
```json
{
  "version": 2,
  "data": {
    "entity_notes": {
      "sensor.temperature": "My note"
    },
    "device_notes": {
      "device_id_123": "Device note"
    }
  }
}
```

## 🐛 Bug Fixes

- Fixed nested dialog detection for device registry dialogs
- Improved shadow DOM detection and injection
- Fixed duplicate note cards appearing in dialogs
- Enhanced error logging for troubleshooting

## 🙏 Acknowledgments

Special thanks to all users who tested and provided feedback during development!

## 📚 Full Changelog

See the [commit history](https://github.com/martindell/ha-entity-notes/compare/v2.2.2...v3.0.0) for detailed changes.
