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

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Entity Notes integration from configuration.yaml."""
    # This is for backward compatibility with configuration.yaml
    # The main setup now happens in async_setup_entry
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Notes from a config entry."""
    _LOGGER.info("Setting up Entity Notes integration")

    # Initialize storage
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    # Load existing notes
    try:
        stored_data = await store.async_load()
        notes_data = stored_data or {}
    except Exception as e:
        _LOGGER.warning("Could not load notes storage, starting fresh: %s", e)
        notes_data = {}

    # Store the storage instance and data in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "store": store,
        "notes": notes_data
    }

    # Register the API view
    hass.http.register_view(EntityNotesView())
    
    # Register the JavaScript file serving view
    hass.http.register_view(EntityNotesJSView())

    # Register frontend resource
    # Serve the JS file directly from the integration
    try:
        # Register the JS file served by our own endpoint
        add_extra_js_url(hass, "/api/entity_notes/entity-notes.js")
        _LOGGER.info("Registered frontend resource: /api/entity_notes/entity-notes.js")
            
    except Exception as e:
        _LOGGER.error("Failed to register frontend resource: %s", e)

    _LOGGER.info("Entity Notes integration setup complete")
    return True

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

class EntityNotesCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
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
                <textarea 
                    class="entity-notes-textarea" 
                    placeholder="Notes"
                    maxlength="200"
                    rows="1"
                ></textarea>
                <div class="entity-notes-char-count">0/200</div>
                <div class="entity-notes-actions">
                    <button class="entity-notes-button entity-notes-delete">Delete</button>
                    <button class="entity-notes-button entity-notes-save">Save</button>
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

        // Auto-resize on focus to handle any content that was loaded
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
        
        // Reset height to auto to get the correct scrollHeight
        textarea.style.height = 'auto';
        
        // Calculate the new height based on content
        const newHeight = Math.max(40, Math.min(300, textarea.scrollHeight));
        
        // Set the new height
        textarea.style.height = newHeight + 'px';
    }

    async loadNote() {
        const entityId = this.getAttribute('entity-id');
        if (!entityId) return;

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`);
            const data = await response.json();
            
            const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
            textarea.value = data.note || '';
            
            // Update character count and resize
            this.updateCharCount();
            
            // Use setTimeout to ensure the textarea is rendered before resizing
            setTimeout(() => {
                this.autoResize();
            }, 10);
            
        } catch (error) {
            console.error('Entity Notes: Error loading note:', error);
        }
    }

    async saveNote() {
        const entityId = this.getAttribute('entity-id');
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const note = textarea.value.trim();

        if (!entityId) return;

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note })
            });

            if (!response.ok) {
                console.error('Entity Notes: Save failed');
            }
        } catch (error) {
            console.error('Entity Notes: Error saving note:', error);
        }
    }

    async deleteNote() {
        const entityId = this.getAttribute('entity-id');
        if (!entityId) return;

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
                textarea.value = '';
                this.updateCharCount();
                this.autoResize();
            }
        } catch (error) {
            console.error('Entity Notes: Error deleting note:', error);
        }
    }
}

if (!customElements.get('entity-notes-card')) {
    customElements.define('entity-notes-card', EntityNotesCard);
}

function getEntityIdFromDialog(dialog) {
    if (dialog._entityId) {
        return dialog._entityId;
    }
    
    if (dialog._entry?.entity_id) {
        return dialog._entry.entity_id;
    }
    
    if (dialog.stateObj?.entity_id) {
        return dialog.stateObj.entity_id;
    }
    
    return null;
}

function injectEntityNotes() {
    const homeAssistant = document.querySelector('home-assistant');
    const shadowRoot = homeAssistant?.shadowRoot;

    if (shadowRoot) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.tagName === 'HA-MORE-INFO-DIALOG') {
                        const delays = [100, 300, 500];
                        delays.forEach((delay) => {
                            setTimeout(() => {
                                const entityId = getEntityIdFromDialog(node);
                                if (entityId) {
                                    addNotesCard(node, entityId);
                                }
                            }, delay);
                        });
                    }
                });
            });
        });

        observer.observe(shadowRoot, { childList: true, subtree: true });
    }
}

function addNotesCard(dialog, entityId) {
    const content = dialog.shadowRoot?.querySelector('.content');
    if (content && !content.querySelector('entity-notes-card') && entityId) {
        const notesCard = document.createElement('entity-notes-card');
        notesCard.setAttribute('entity-id', entityId);
        content.appendChild(notesCard);
        
        setTimeout(() => {
            notesCard.loadNote();
        }, 100);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectEntityNotes);
} else {
    injectEntityNotes();
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

