
# Entity Notes

Add custom notes to any Home Assistant entity through the "more info" dialog.

## Features

- **Universal compatibility** - Works with all Home Assistant entities
- **Persistent storage** - Notes survive restarts and updates
- **Auto-resizing interface** - Text area adapts to content length
- **Character limit** - 200 character limit with visual feedback
- **Instant saving** - Changes are saved automatically
- **Clean interface** - Seamlessly integrates with Home Assistant's UI

## Perfect for:

- 📍 **Device locations** - "Living room lamp, behind the couch"
- 🔧 **Maintenance notes** - "Last cleaned: 2024-01-15"
- ⚙️ **Configuration details** - "Configured for motion detection"
- 📝 **General reminders** - "Replace battery when below 20%"

## Installation

After installation through HACS, add this to your `configuration.yaml`:

```yaml
frontend:
  extra_module_url:
    - /local/entity-notes.js
```

Then restart Home Assistant and start adding notes to your entities!
