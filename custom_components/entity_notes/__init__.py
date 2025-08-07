"""Entity Notes integration for Home Assistant."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.storage import Store
from homeassistant.components.frontend import add_extra_js_url
from aiohttp import web
import json
import os

_LOGGER = logging.getLogger(__name__)

DOMAIN = "entity_notes"
STORAGE_VERSION = 1
STORAGE_KEY = "entity_notes.notes"

# Module-level debug log to see if this file is being loaded
_LOGGER.warning("🔧 DEBUG: __init__.py module loaded for domain: %s", DOMAIN)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Entity Notes integration from configuration.yaml."""
    _LOGGER.warning("🔧 DEBUG: async_setup called with config: %s", config)
    # This is for backward compatibility with configuration.yaml
    # The main setup now happens in async_setup_entry
    _LOGGER.warning("🔧 DEBUG: async_setup completed successfully")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    _LOGGER.warning("🔧 DEBUG: async_setup_entry called with entry: %s", entry)
    _LOGGER.warning("🔧 DEBUG: Entry data: %s", entry.data)
    _LOGGER.warning("🔧 DEBUG: Entry domain: %s", entry.domain)
    _LOGGER.warning("🔧 DEBUG: Entry title: %s", entry.title)
    
    try:
        _LOGGER.warning("🔧 DEBUG: Starting Entity Notes integration setup")

        # Initialize storage
        _LOGGER.warning("🔧 DEBUG: Initializing storage")
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        # Load existing notes
        try:
            _LOGGER.warning("🔧 DEBUG: Loading existing notes from storage")
            stored_data = await store.async_load()
            notes_data = stored_data or {}
            _LOGGER.warning("🔧 DEBUG: Loaded %d existing notes", len(notes_data))
        except Exception as e:
            _LOGGER.warning("🔧 DEBUG: Could not load notes storage, starting fresh: %s", e)
            notes_data = {}

        # Store the storage instance and data in hass.data
        _LOGGER.warning("🔧 DEBUG: Setting up hass.data for domain %s", DOMAIN)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN] = {
            "store": store,
            "notes": notes_data
        }
        _LOGGER.warning("🔧 DEBUG: hass.data setup complete")

        # Register the API view
        _LOGGER.warning("🔧 DEBUG: Registering EntityNotesView")
        hass.http.register_view(EntityNotesView())
        _LOGGER.warning("🔧 DEBUG: EntityNotesView registered successfully")
        
        # Register the JavaScript file serving view
        _LOGGER.warning("🔧 DEBUG: Registering EntityNotesJSView")
        hass.http.register_view(EntityNotesJSView())
        _LOGGER.warning("🔧 DEBUG: EntityNotesJSView registered successfully")

        # Register frontend resource
        # Serve the JS file directly from the integration
        try:
            _LOGGER.warning("🔧 DEBUG: Registering frontend resource")
            # Register the JS file served by our own endpoint
            add_extra_js_url(hass, "/api/entity_notes/entity-notes.js")
            _LOGGER.warning("🔧 DEBUG: Frontend resource registered: /api/entity_notes/entity-notes.js")
                
        except Exception as e:
            _LOGGER.error("🔧 DEBUG: Failed to register frontend resource: %s", e)

        _LOGGER.warning("🔧 DEBUG: Entity Notes integration setup complete successfully")
        return True
        
    except Exception as e:
        _LOGGER.error("🔧 DEBUG: CRITICAL ERROR in async_setup_entry: %s", e)
        _LOGGER.error("🔧 DEBUG: Exception type: %s", type(e).__name__)
        import traceback
        _LOGGER.error("🔧 DEBUG: Full traceback: %s", traceback.format_exc())
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Clean up if needed
    return True

class EntityNotesView(HomeAssistantView):
    """Handle Entity Notes API requests."""

    url = "/api/entity_notes/{entity_id}"
    name = "api:entity_notes"
    requires_auth = False  # Simplified - no auth required for local requests

    async def get(self, request, entity_id):
        """Get note for an entity."""
        hass = request.app["hass"]
        notes_data = hass.data[DOMAIN]["notes"]

        note = notes_data.get(entity_id, "")
        _LOGGER.debug("Retrieved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
        return web.json_response({"note": note})

    async def post(self, request, entity_id):
        """Save note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        notes_data = hass.data[DOMAIN]["notes"]

        try:
            data = await request.json()
            note = data.get("note", "").strip()

            if note:
                notes_data[entity_id] = note
                _LOGGER.info("Saved note for %s: %s", entity_id, note[:50] + "..." if len(note) > 50 else note)
            else:
                # Remove empty notes
                notes_data.pop(entity_id, None)
                _LOGGER.info("Removed empty note for %s", entity_id)

            # Save to persistent storage
            await store.async_save(notes_data)

            return web.json_response({"status": "success"})

        except Exception as e:
            _LOGGER.error("Error saving note for %s: %s", entity_id, e)
            return web.json_response({"error": str(e)}, status=500)

    async def delete(self, request, entity_id):
        """Delete note for an entity."""
        hass = request.app["hass"]
        store = hass.data[DOMAIN]["store"]
        notes_data = hass.data[DOMAIN]["notes"]

        try:
            if entity_id in notes_data:
                del notes_data[entity_id]
                _LOGGER.info("Deleted note for %s", entity_id)

                # Save to persistent storage
                await store.async_save(notes_data)

                return web.json_response({"status": "deleted"})
            else:
                return web.json_response({"status": "not_found"}, status=404)

        except Exception as e:
            _LOGGER.error("Error deleting note for %s: %s", entity_id, e)
            return web.json_response({"error": str(e)}, status=500)

class EntityNotesJSView(HomeAssistantView):
    """Serve the Entity Notes JavaScript file."""

    url = "/api/entity_notes/entity-notes.js"
    name = "api:entity_notes_js"
    requires_auth = False

    # Embedded JavaScript content to avoid file I/O operations
    JS_CONTENT = """console.log('Entity Notes: Script loading...');

// Create global namespace for debugging
window.entityNotes = {
    version: '1.0.4-fixed',
    debug: true
};

class EntityNotesCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        console.log('Entity Notes: EntityNotesCard constructor called');
    }

    connectedCallback() {
        console.log('Entity Notes: EntityNotesCard connected');
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                .entity-notes-container {
                    margin: 16px 0;
                    padding: 16px;
                    border: 1px solid var(--divider-color, #e0e0e0);
                    border-radius: 8px;
                    background: var(--card-background-color, white);
                }
                .entity-notes-title {
                    font-weight: 500;
                    margin-bottom: 8px;
                    color: var(--primary-text-color, black);
                }
                .entity-notes-textarea {
                    width: 100%;
                    min-height: 40px;
                    max-height: 300px;
                    padding: 8px;
                    border: 1px solid var(--divider-color, #e0e0e0);
                    border-radius: 4px;
                    background: var(--primary-background-color, white);
                    color: var(--primary-text-color, black);
                    font-family: inherit;
                    font-size: 14px;
                    line-height: 1.4;
                    resize: none;
                    overflow: hidden;
                    box-sizing: border-box;
                    transition: height 0.1s ease;
                }
                .entity-notes-textarea:focus {
                    outline: 2px solid var(--primary-color, #03a9f4);
                    outline-offset: -2px;
                }
                .entity-notes-actions {
                    display: flex;
                    gap: 8px;
                    margin-top: 8px;
                    justify-content: flex-end;
                }
                .entity-notes-button {
                    padding: 6px 12px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: 500;
                    text-transform: uppercase;
                }
                .entity-notes-save {
                    background: var(--primary-color, #03a9f4);
                    color: white;
                }
                .entity-notes-delete {
                    background: var(--error-color, #f44336);
                    color: white;
                }
                .entity-notes-char-count {
                    font-size: 11px;
                    color: var(--secondary-text-color, #666);
                    margin-top: 4px;
                    text-align: right;
                }
                .entity-notes-char-count.warning {
                    color: var(--warning-color, #ff9800);
                }
                .entity-notes-char-count.error {
                    color: var(--error-color, #f44336);
                }
            </style>
            <div class="entity-notes-container">
                <div class="entity-notes-title">Notes</div>
                <textarea 
                    class="entity-notes-textarea" 
                    placeholder="Add notes for this entity..."
                    maxlength="200"
                    rows="1"
                ></textarea>
                <div class="entity-notes-char-count">0/200</div>
                <div class="entity-notes-actions">
                    <button class="entity-notes-button entity-notes-delete">DELETE</button>
                    <button class="entity-notes-button entity-notes-save">SAVE</button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const charCount = this.shadowRoot.querySelector('.entity-notes-char-count');
        const saveBtn = this.shadowRoot.querySelector('.entity-notes-save');
        const deleteBtn = this.shadowRoot.querySelector('.entity-notes-delete');

        textarea.addEventListener('input', () => {
            this.updateCharCount();
            this.autoResize();
        });

        textarea.addEventListener('focus', () => {
            this.autoResize();
        });

        saveBtn.addEventListener('click', () => this.saveNote());
        deleteBtn.addEventListener('click', () => this.deleteNote());
    }

    updateCharCount() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const charCount = this.shadowRoot.querySelector('.entity-notes-char-count');
        const count = textarea.value.length;
        
        charCount.textContent = `${count}/200`;
        
        charCount.classList.remove('warning', 'error');
        if (count > 180) charCount.classList.add('warning');
        if (count > 200) charCount.classList.add('error');
    }

    autoResize() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        textarea.style.height = 'auto';
        const newHeight = Math.max(40, Math.min(300, textarea.scrollHeight));
        textarea.style.height = newHeight + 'px';
    }

    async loadNote() {
        const entityId = this.getAttribute('entity-id');
        console.log('Entity Notes: Loading note for', entityId);
        if (!entityId) return;

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`);
            const data = await response.json();
            
            const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
            textarea.value = data.note || '';
            
            this.updateCharCount();
            setTimeout(() => this.autoResize(), 10);
            
        } catch (error) {
            console.error('Entity Notes: Error loading note:', error);
        }
    }

    async saveNote() {
        const entityId = this.getAttribute('entity-id');
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const note = textarea.value.trim();

        console.log('Entity Notes: Saving note for', entityId, ':', note);

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note })
            });

            if (response.ok) {
                console.log('Entity Notes: Note saved successfully');
            } else {
                console.error('Entity Notes: Save failed');
            }
        } catch (error) {
            console.error('Entity Notes: Error saving note:', error);
        }
    }

    async deleteNote() {
        const entityId = this.getAttribute('entity-id');
        console.log('Entity Notes: Deleting note for', entityId);

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
                textarea.value = '';
                this.updateCharCount();
                this.autoResize();
                console.log('Entity Notes: Note deleted successfully');
            }
        } catch (error) {
            console.error('Entity Notes: Error deleting note:', error);
        }
    }
}

// Register both element names for compatibility
if (!customElements.get('entity-notes-card')) {
    customElements.define('entity-notes-card', EntityNotesCard);
    console.log('Entity Notes: Custom element entity-notes-card registered');
}

if (!customElements.get('entity-notes')) {
    customElements.define('entity-notes', EntityNotesCard);
    console.log('Entity Notes: Custom element entity-notes registered');
}

// Store reference for debugging
window.entityNotes.EntityNotesCard = EntityNotesCard;

function findEntityId(dialog) {
    console.log('Entity Notes: Finding entity ID for dialog', dialog);
    
    // Try multiple methods to get entity ID
    const methods = [
        () => dialog.stateObj?.entity_id,
        () => dialog._stateObj?.entity_id,
        () => dialog.entityId,
        () => dialog._entityId,
        () => dialog.getAttribute?.('entity-id'),
        () => dialog.dataset?.entityId,
        () => {
            const stateObj = dialog.querySelector?.('[state-obj]')?.stateObj;
            return stateObj?.entity_id;
        }
    ];
    
    for (const method of methods) {
        try {
            const entityId = method();
            if (entityId) {
                console.log('Entity Notes: Found entity ID:', entityId);
                return entityId;
            }
        } catch (e) {
            // Continue to next method
        }
    }
    
    console.log('Entity Notes: No entity ID found');
    return null;
}

function injectNotesIntoDialog(dialog) {
    console.log('Entity Notes: Attempting to inject notes into dialog', dialog);
    
    if (!dialog || !dialog.shadowRoot) {
        console.log('Entity Notes: No dialog or shadowRoot found');
        return;
    }
    
    // Check if already injected
    if (dialog.shadowRoot.querySelector('entity-notes-card')) {
        console.log('Entity Notes: Notes already injected');
        return;
    }
    
    const entityId = findEntityId(dialog);
    if (!entityId) {
        console.log('Entity Notes: No entity ID found for dialog');
        return;
    }
    
    // Try multiple selectors to find content area
    const selectors = [
        '.content',
        '.mdc-dialog__content',
        '[slot="content"]',
        '.dialog-content',
        'ha-dialog-content'
    ];
    
    let contentArea = null;
    for (const selector of selectors) {
        contentArea = dialog.shadowRoot.querySelector(selector);
        if (contentArea) {
            console.log('Entity Notes: Found content area with selector:', selector);
            break;
        }
    }
    
    if (!contentArea) {
        console.log('Entity Notes: No content area found');
        return;
    }
    
    // Create and inject notes card
    const notesCard = document.createElement('entity-notes-card');
    notesCard.setAttribute('entity-id', entityId);
    contentArea.appendChild(notesCard);
    
    console.log('Entity Notes: Notes card injected for entity:', entityId);
    
    // Load the note after a short delay
    setTimeout(() => {
        notesCard.loadNote();
    }, 100);
}

function setupDialogObserver() {
    console.log('Entity Notes: Setting up dialog observer');
    
    const homeAssistant = document.querySelector('home-assistant');
    if (!homeAssistant?.shadowRoot) {
        console.log('Entity Notes: Home Assistant shadow root not found, retrying in 1 second...');
        setTimeout(setupDialogObserver, 1000);
        return;
    }
    
    // Observer specifically for Home Assistant shadow DOM
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    console.log('Entity Notes: Node added to shadow DOM:', node.tagName);
                    
                    // Check if this is a more-info dialog
                    if (node.tagName === 'HA-MORE-INFO-DIALOG') {
                        console.log('Entity Notes: More-info dialog detected:', node);
                        
                        // Try injection with multiple delays to ensure dialog is fully loaded
                        [100, 300, 600, 1000].forEach(delay => {
                            setTimeout(() => {
                                console.log(`Entity Notes: Attempting injection after ${delay}ms delay`);
                                injectNotesIntoDialog(node);
                            }, delay);
                        });
                    }
                    
                    // Also check for nested dialogs
                    const nestedDialogs = node.querySelectorAll?.('ha-more-info-dialog');
                    nestedDialogs?.forEach(dialog => {
                        console.log('Entity Notes: Found nested dialog:', dialog);
                        [100, 300, 600].forEach(delay => {
                            setTimeout(() => injectNotesIntoDialog(dialog), delay);
                        });
                    });
                }
            });
        });
    });
    
    // Observe the Home Assistant shadow root (where dialogs are actually created)
    console.log('Entity Notes: Observing home-assistant shadow root');
    observer.observe(homeAssistant.shadowRoot, { 
        childList: true, 
        subtree: true 
    });
    
    // Also check for existing dialogs in shadow root
    const existingDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
    if (existingDialogs.length > 0) {
        console.log('Entity Notes: Found existing dialogs in shadow root:', existingDialogs.length);
        existingDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });
    }
    
    window.entityNotes.observer = observer;
    console.log('Entity Notes: Observer setup complete');
}

// Initialize when DOM is ready
function initialize() {
    console.log('Entity Notes: Initializing...');
    setupDialogObserver();
    
    // Try to inject into any existing dialogs in shadow DOM
    const homeAssistant = document.querySelector('home-assistant');
    if (homeAssistant?.shadowRoot) {
        const existingDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
        console.log('Entity Notes: Found existing dialogs during init:', existingDialogs.length);
        existingDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });
    }
    
    console.log('Entity Notes: Initialization complete');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

console.log('Entity Notes: Script loaded successfully');"""

    async def get(self, request):
        """Serve the JavaScript file."""
        try:
            _LOGGER.debug("Serving embedded JavaScript content")
            return web.Response(text=self.JS_CONTENT, content_type="application/javascript")
            
        except Exception as e:
            _LOGGER.error("Error serving JavaScript file: %s", e)
            return web.Response(text="// Error loading JavaScript file", content_type="application/javascript", status=500)

