# Entity Notes for Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/default)
[![Latest release](https://img.shields.io/github/v/release/martindell/ha-entity-notes?display_name=tag&sort=semver)](https://github.com/martindell/ha-entity-notes/releases)
[![Downloads](https://img.shields.io/github/downloads/martindell/ha-entity-notes/total)](https://github.com/martindell/ha-entity-notes/releases)
[![Issues](https://img.shields.io/github/issues/martindell/ha-entity-notes)](https://github.com/martindell/ha-entity-notes/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=martindell&repository=ha-entity-notes&category=integration)


A Home Assistant integration that allows you to add custom notes to any entity using the
“more info” dialog. Perfect for documenting device locations, maintenance schedules,
configuration details, or any other information you want to keep with your entities.


## Features
<img
  src="icon.png"
  alt="Entity Notes in action"
  width="125"
  align="right"
/>
- 🗒️ **Add notes to any entity** - Works with all Home Assistant entities (lights, sensors, switches, etc.)
- 💾 **Persistent storage** - Notes are saved permanently and survive restarts
- 🎨 **Auto-resizing textarea** - Input field automatically adjusts to content size
- 📱 **Responsive design** - Works on desktop and mobile
- 🔒 **Local storage** - All data stays on your Home Assistant instance
- ⚡ **Real-time updates** - Changes are saved instantly
- 🎯 **Character limit** - Configurable 200 character limit with visual feedback

## Screenshot

The Entity Notes integration adds a notes section to every entity's "more info" dialog, allowing you to quickly add, edit, or delete notes associated with that entity.

<div align="center">
  <img src="screenshot.png" alt="Entity Notes in action" width="500">
</div>

*Example showing the Entity Notes feature in an entity's more info dialog with a note displayed below the history chart.*

## Installation

## Installation (HACS)
1. In Home Assistant, open **HACS → Integrations**  
2. Search for **Entity Notes**  
3. Install the integration  
4. **Restart Home Assistant**

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/martindell/ha-entity-notes/releases)
2. Extract the contents
3. Copy the `custom_components/entity_notes` folder to your Home Assistant `custom_components` directory
4. Restart Home Assistant

## Configuration

### Integration Setup

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Entity Notes"
4. Click to add the integration
5. The integration will be set up automatically
6. The integration automatically registers its frontend JavaScript file when loaded

## Usage

1. Click on any entity to open its "more info" dialog
2. Scroll down to find the "Notes" section
3. Click in the text area to add or edit notes
4. Use the "Save" button to save
5. Use the "Delete" button to remove notes entirely

### Tips

- Notes are limited to 200 characters (can be changed in integration settings)
- The text area automatically resizes based on content
- Empty notes are automatically removed to keep storage clean
- All notes are stored locally on your Home Assistant instance

## File Structure

```
ha-entity-notes/
├── custom_components/
│   └── entity_notes/
│       ├── __init__.py         # Main integration logic and API endpoints
│       ├── manifest.json       # Integration manifest
│       ├── const.py            # Constants and configuration
│       └── services.yaml       # Service definitions
├── www/
│   └── entity-notes.js         # Frontend JavaScript component
├── hacs.json                   # HACS configuration
├── README.md                   # This documentation
└── info.md                     # HACS info file
```

### File Descriptions

- **`__init__.py`** - Contains the main integration setup, storage management, and REST API endpoints for saving/loading notes
- **`manifest.json`** - Home Assistant integration manifest defining dependencies, version, and metadata
- **`const.py`** - Defines constants used throughout the integration
- **`services.yaml`** - Defines any services exposed by the integration
- **`entity-notes.js`** - Frontend component that injects the notes interface into entity dialogs
- **`hacs.json`** - HACS configuration file specifying compatibility and requirements

## API Endpoints

The integration exposes REST API endpoints for managing notes:

- `GET /api/entity_notes/{entity_id}` - Retrieve note for an entity
- `POST /api/entity_notes/{entity_id}` - Save note for an entity
- `DELETE /api/entity_notes/{entity_id}` - Delete note for an entity

## Storage

Notes are stored in Home Assistant's internal storage system at `.storage/entity_notes.notes`. The storage is automatically managed and persisted across restarts.

## Troubleshooting

### Notes not appearing
- Clear browser cache and / or force refresh.  On mobile, clear the app cache
- Restart Home Assistant after configuration changes

### Notes not saving
- Check Home Assistant logs for any error messages
- Ensure the integration is properly installed and loaded
- Verify file permissions in the Home Assistant directory

### Browser console errors
- Open browser developer tools and check for JavaScript errors
- Ensure the script is loading properly: `entity-notes.js`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Search existing [issues](https://github.com/martindell/ha-entity-notes/issues)
3. Create a new issue with detailed information about your problem
