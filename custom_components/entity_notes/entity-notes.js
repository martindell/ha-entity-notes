console.log('Entity Notes: Script loading...');

// Create global namespace with configuration from backend
window.entityNotes = {
    version: '1.3.0',
    debug: {{DEBUG_LOGGING}},
    maxNoteLength: {{MAX_NOTE_LENGTH}},
    
    // Convenience methods for users
    enableDebug: function() { 
        this.debug = true; 
        console.log('Entity Notes: Debug mode enabled. Refresh page or open entity dialogs to see debug output.');
    },
    disableDebug: function() { 
        this.debug = false; 
        console.log('Entity Notes: Debug mode disabled.');
    }
};

// Debug logging function - only logs when debug mode is enabled
function debugLog(message) {
    if (window.entityNotes.debug) {
        console.log(message);
    }
}

// Always log critical messages (errors, warnings, success)
function infoLog(message) {
    console.log(message);
}

class EntityNotesCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        debugLog('Entity Notes: EntityNotesCard constructor called');
    }

    connectedCallback() {
        debugLog('Entity Notes: EntityNotesCard connected');
        this.render();
        this.setupEventListeners();
    }

    render() {
        const maxLength = window.entityNotes.maxNoteLength;
        this.shadowRoot.innerHTML = `
            <style>
                .entity-notes-container {
                    margin: 8px 0;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                    background: transparent;
                }
                .entity-notes-textarea {
                    width: 100%;
                    min-height: 36px;
                    max-height: 300px;
                    padding: 6px 8px;
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
                    outline: none;
                }
                .entity-notes-textarea:focus {
                    border-color: var(--primary-color, #03a9f4);
                    box-shadow: 0 0 0 1px var(--primary-color, #03a9f4);
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
                    maxlength="${maxLength}"
                    rows="1"
                ></textarea>
                <div class="entity-notes-char-count">0/${maxLength}</div>
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
        const maxLength = window.entityNotes.maxNoteLength;
        
        charCount.textContent = `${count}/${maxLength}`;
        
        charCount.classList.remove('warning', 'error');
        if (count > maxLength * 0.9) charCount.classList.add('warning');
        if (count >= maxLength) charCount.classList.add('error');
    }

    autoResize() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        textarea.style.height = 'auto';
        const newHeight = Math.max(40, Math.min(300, textarea.scrollHeight));
        textarea.style.height = newHeight + 'px';
    }

    async loadNote() {
        const entityId = this.getAttribute('entity-id');
        debugLog('Entity Notes: Loading note for ' + entityId);
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

        debugLog('Entity Notes: Saving note for ' + entityId + ': ' + note);

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note })
            });

            if (response.ok) {
                debugLog('Entity Notes: Note saved successfully');
            } else {
                console.error('Entity Notes: Save failed');
            }
        } catch (error) {
            console.error('Entity Notes: Error saving note:', error);
        }
    }

    async deleteNote() {
        const entityId = this.getAttribute('entity-id');
        debugLog('Entity Notes: Deleting note for ' + entityId);

        try {
            const response = await fetch(`/api/entity_notes/${entityId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
                textarea.value = '';
                this.updateCharCount();
                this.autoResize();
                debugLog('Entity Notes: Note deleted successfully');
            }
        } catch (error) {
            console.error('Entity Notes: Error deleting note:', error);
        }
    }
}

// Register the custom element
if (!customElements.get('entity-notes-card')) {
    customElements.define('entity-notes-card', EntityNotesCard);
    infoLog('Entity Notes: Integration loaded successfully');
}

// Store reference for debugging
window.entityNotes.EntityNotesCard = EntityNotesCard;

function findEntityId(dialog) {
    debugLog('Entity Notes: Finding entity ID for dialog');
    
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
                debugLog('Entity Notes: Found entity ID: ' + entityId);
                return entityId;
            }
        } catch (e) {
            // Continue to next method
        }
    }
    
    debugLog('Entity Notes: No entity ID found');
    return null;
}

function injectNotesIntoDialog(dialog) {
    debugLog('Entity Notes: Attempting to inject notes into dialog');
    
    if (!dialog || !dialog.shadowRoot) {
        debugLog('Entity Notes: No dialog or shadowRoot found');
        return;
    }
    
    // Check if already injected
    if (dialog.shadowRoot.querySelector('entity-notes-card')) {
        debugLog('Entity Notes: Notes already injected');
        return;
    }
    
    const entityId = findEntityId(dialog);
    if (!entityId) {
        debugLog('Entity Notes: No entity ID found for dialog');
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
            debugLog('Entity Notes: Found content area with selector: ' + selector);
            break;
        }
    }
    
    if (!contentArea) {
        debugLog('Entity Notes: No content area found');
        return;
    }
    
    // Create and inject notes card
    const notesCard = document.createElement('entity-notes-card');
    notesCard.setAttribute('entity-id', entityId);
    contentArea.appendChild(notesCard);
    
    debugLog('Entity Notes: Notes card injected for entity: ' + entityId);
    
    // Load the note after a short delay
    setTimeout(() => {
        notesCard.loadNote();
    }, 100);
}

function setupDialogObserver() {
    debugLog('Entity Notes: Setting up dialog observer');
    
    const homeAssistant = document.querySelector('home-assistant');
    if (!homeAssistant?.shadowRoot) {
        debugLog('Entity Notes: Home Assistant shadow root not found, retrying in 1 second...');
        setTimeout(setupDialogObserver, 1000);
        return;
    }
    
    // Observer specifically for Home Assistant shadow DOM
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    debugLog('Entity Notes: Node added to shadow DOM: ' + node.tagName);
                    
                    // Check if this is a more-info dialog
                    if (node.tagName === 'HA-MORE-INFO-DIALOG') {
                        debugLog('Entity Notes: More-info dialog detected');
                        
                        // Try injection with multiple delays to ensure dialog is fully loaded
                        [100, 300, 600, 1000].forEach(delay => {
                            setTimeout(() => {
                                debugLog('Entity Notes: Attempting injection after ' + delay + 'ms delay');
                                injectNotesIntoDialog(node);
                            }, delay);
                        });
                    }
                    
                    // Also check for nested dialogs
                    const nestedDialogs = node.querySelectorAll?.('ha-more-info-dialog');
                    nestedDialogs?.forEach(dialog => {
                        debugLog('Entity Notes: Found nested dialog');
                        [100, 300, 600].forEach(delay => {
                            setTimeout(() => injectNotesIntoDialog(dialog), delay);
                        });
                    });
                }
            });
        });
    });
    
    // Observe the Home Assistant shadow root (where dialogs are actually created)
    debugLog('Entity Notes: Observing home-assistant shadow root');
    observer.observe(homeAssistant.shadowRoot, { 
        childList: true, 
        subtree: true 
    });
    
    // Also check for existing dialogs in shadow root
    const existingDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
    if (existingDialogs.length > 0) {
        debugLog('Entity Notes: Found existing dialogs in shadow root: ' + existingDialogs.length);
        existingDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });
    }
    
    window.entityNotes.observer = observer;
    infoLog('Entity Notes: Observer setup complete');
}

// Initialize when DOM is ready
function initialize() {
    debugLog('Entity Notes: Initializing...');
    setupDialogObserver();
    
    // Try to inject into any existing dialogs in shadow DOM
    const homeAssistant = document.querySelector('home-assistant');
    if (homeAssistant?.shadowRoot) {
        const existingDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
        debugLog('Entity Notes: Found existing dialogs during init: ' + existingDialogs.length);
        existingDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });
    }
    
    debugLog('Entity Notes: Initialization complete');
}

// Make initialize function globally accessible for debugging
window.entityNotes.initialize = initialize;

// Robust initialization with error handling
function initializeWithErrorHandling() {
    try {
        debugLog('Entity Notes: Starting initialization...');
        debugLog('Entity Notes: DOM ready state: ' + document.readyState);
        
        initialize();
        
        infoLog('Entity Notes: Initialization completed successfully');
    } catch (error) {
        console.error('Entity Notes: Initialization failed:', error);
        console.error('Entity Notes: Error stack:', error.stack);
        
        // Try fallback initialization after delay
        setTimeout(() => {
            try {
                debugLog('Entity Notes: Attempting fallback initialization...');
                initialize();
            } catch (fallbackError) {
                console.error('Entity Notes: Fallback initialization also failed:', fallbackError);
            }
        }, 3000);
    }
}

// Handle all DOM ready scenarios
if (document.readyState === 'loading') {
    debugLog('Entity Notes: DOM still loading, waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', initializeWithErrorHandling);
} else {
    debugLog('Entity Notes: DOM already ready, initializing immediately...');
    // Use setTimeout to ensure this runs after the current execution stack
    setTimeout(initializeWithErrorHandling, 0);
}

// Additional fallback: try initialization after a delay regardless
setTimeout(() => {
    if (!window.entityNotes.observer) {
        debugLog('Entity Notes: Observer not found, triggering fallback initialization...');
        initializeWithErrorHandling();
    } else {
        debugLog('Entity Notes: Observer already exists, no fallback needed');
    }
}, 2000);

infoLog('Entity Notes: Script loaded successfully');