// Entity Notes Integration - Final Working Version
(function() {
    'use strict';

    // Configuration from backend
    const debugLogging = "{{DEBUG_LOGGING}}" === "true";
    const maxNoteLength = parseInt("{{MAX_NOTE_LENGTH}}", 10) || 250;
    const hideButtonsWhenEmpty = "{{HIDE_BUTTONS_WHEN_EMPTY}}" === "true";

    console.log(`Entity Notes: Script loaded successfully. Version 1.3.0 (Hide buttons when empty: ${hideButtonsWhenEmpty}, Max length: ${maxNoteLength})`);

    // Track processed dialogs to prevent duplicates
    const processedDialogs = new Map();

    // Custom element for notes card
    class EntityNotesCard extends HTMLElement {
        constructor() {
            super();
            this.entityId = this.getAttribute('entity-id') || 'unknown';
            this.hasExistingNote = false;
            console.log('Entity Notes: EntityNotesCard constructor called');
        }

        connectedCallback() {
            console.log('Entity Notes: EntityNotesCard connected');
            this.render();
            this.loadNote();
        }

        render() {
            const initialButtonClass = hideButtonsWhenEmpty ? 'entity-notes-actions hidden' : 'entity-notes-actions';
            console.log(`Entity Notes: Rendering with hideButtonsWhenEmpty=${hideButtonsWhenEmpty}, initial class=${initialButtonClass}`);
            
            this.innerHTML = `
                <style>
                    .entity-notes-container {
                        margin: 16px 0;
                        padding: 16px;
                        border: 1px solid var(--divider-color);
                        border-radius: 8px;
                        background: var(--card-background-color);
                    }
                    .entity-notes-header {
                        display: flex;
                        align-items: center;
                        margin-bottom: 12px;
                        font-weight: 500;
                        color: var(--primary-text-color);
                    }
                    .entity-notes-textarea {
                        width: 100%;
                        min-height: 80px;
                        padding: 8px;
                        border: 1px solid var(--divider-color);
                        border-radius: 4px;
                        background: var(--primary-background-color);
                        color: var(--primary-text-color);
                        font-family: inherit;
                        font-size: 14px;
                        resize: vertical;
                        box-sizing: border-box;
                    }
                    .entity-notes-textarea:focus {
                        outline: none;
                        border-color: var(--primary-color);
                    }
                    .entity-notes-actions {
                        display: flex;
                        justify-content: flex-end;
                        gap: 8px;
                        margin-top: 12px;
                    }
                    .entity-notes-actions.hidden {
                        display: none;
                    }
                    .entity-notes-button {
                        padding: 8px 16px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: 500;
                    }
                    .entity-notes-save {
                        background: var(--primary-color);
                        color: var(--text-primary-color);
                    }
                    .entity-notes-delete {
                        background: var(--error-color);
                        color: white;
                    }
                    .entity-notes-counter {
                        text-align: right;
                        font-size: 12px;
                        color: var(--secondary-text-color);
                        margin-top: 4px;
                    }
                </style>
                <div class="entity-notes-container">
                    <div class="entity-notes-header">
                        📝 Notes
                    </div>
                    <textarea 
                        class="entity-notes-textarea" 
                        placeholder="Add your notes here..."
                        maxlength="${maxNoteLength}"></textarea>
                    <div class="entity-notes-counter">
                        <span class="char-count">0</span>/${maxNoteLength}
                    </div>
                    <div class="${initialButtonClass}">
                        <button class="entity-notes-button entity-notes-delete">DELETE</button>
                        <button class="entity-notes-button entity-notes-save">SAVE</button>
                    </div>
                </div>
            `;

            this.setupEventListeners();
        }

        setupEventListeners() {
            const textarea = this.querySelector('.entity-notes-textarea');
            const saveButton = this.querySelector('.entity-notes-save');
            const deleteButton = this.querySelector('.entity-notes-delete');
            const charCount = this.querySelector('.char-count');

            // Update character count
            textarea.addEventListener('input', () => {
                charCount.textContent = textarea.value.length;
                this.updateButtonVisibility();
            });

            // Save note
            saveButton.addEventListener('click', () => this.saveNote());

            // Delete note
            deleteButton.addEventListener('click', () => this.deleteNote());
        }

        updateButtonVisibility() {
            if (!hideButtonsWhenEmpty) {
                console.log('Entity Notes: Always showing buttons (user preference - hideButtonsWhenEmpty is false)');
                return;
            }

            const textarea = this.querySelector('.entity-notes-textarea');
            const actions = this.querySelector('.entity-notes-actions');
            const currentText = textarea.value.trim();
            
            console.log('Entity Notes: updateButtonVisibility called');
            console.log(`  - hideButtonsWhenEmpty: ${hideButtonsWhenEmpty}`);
            console.log(`  - currentText: "${currentText}"`);
            console.log(`  - hasExistingNote: ${this.hasExistingNote}`);

            const shouldShowButtons = currentText.length > 0 || this.hasExistingNote;
            console.log(`  - shouldShowButtons: ${shouldShowButtons}`);

            if (shouldShowButtons) {
                actions.classList.remove('hidden');
                console.log('Entity Notes: Showing buttons - has text or existing note');
                console.log(`  - Final button classes: ${actions.className}`);
            } else {
                actions.classList.add('hidden');
                console.log('Entity Notes: Hiding buttons - no text and no existing note');
                console.log(`  - Final button classes: ${actions.className}`);
            }
        }

        async loadNote() {
            console.log(`Entity Notes: Loading note for ${this.entityId}`);
            try {
                const response = await fetch(`/api/entity_notes/${this.entityId}`);
                const data = await response.json();
                const note = data.note || '';
                
                console.log(`Entity Notes: Note loaded - hasExistingNote set to: ${!!note}`);
                console.log(`Entity Notes: Note content: "${note}"`);
                
                this.hasExistingNote = !!note;
                
                const textarea = this.querySelector('.entity-notes-textarea');
                const charCount = this.querySelector('.char-count');
                
                textarea.value = note;
                charCount.textContent = note.length;
                
                this.updateButtonVisibility();
                
                console.log(`Entity Notes: Note loaded successfully for ${this.entityId}`);
            } catch (error) {
                console.error(`Entity Notes: Error loading note for ${this.entityId}:`, error);
            }
        }

        async saveNote() {
            const textarea = this.querySelector('.entity-notes-textarea');
            const note = textarea.value.trim();
            
            try {
                const response = await fetch(`/api/entity_notes/${this.entityId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ note })
                });
                
                if (response.ok) {
                    this.hasExistingNote = !!note;
                    this.updateButtonVisibility();
                    console.log(`Entity Notes: Note saved for ${this.entityId}`);
                } else {
                    console.error('Entity Notes: Failed to save note');
                }
            } catch (error) {
                console.error('Entity Notes: Error saving note:', error);
            }
        }

        async deleteNote() {
            try {
                const response = await fetch(`/api/entity_notes/${this.entityId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    const textarea = this.querySelector('.entity-notes-textarea');
                    const charCount = this.querySelector('.char-count');
                    
                    textarea.value = '';
                    charCount.textContent = '0';
                    this.hasExistingNote = false;
                    this.updateButtonVisibility();
                    
                    console.log(`Entity Notes: Note deleted for ${this.entityId}`);
                } else {
                    console.error('Entity Notes: Failed to delete note');
                }
            } catch (error) {
                console.error('Entity Notes: Error deleting note:', error);
            }
        }
    }

    // Register custom element
    if (!customElements.get('entity-notes-card')) {
        customElements.define('entity-notes-card', EntityNotesCard);
    }

    // Enhanced entity ID extraction
    function extractEntityId(dialog) {
        // Try multiple methods to get entity ID
        const methods = [
            () => dialog.stateObj?.entity_id,
            () => dialog.entityId,
            () => dialog.getAttribute?.('data-entity-id'),
            () => dialog._entityId,
            () => {
                // Look for entity ID in dialog content
                const content = dialog.shadowRoot?.querySelector('ha-dialog')?.textContent || '';
                const match = content.match(/([a-z_]+\.[a-z0-9_]+)/);
                return match?.[1];
            },
            () => {
                // Check hass object for current entity
                const hass = dialog.hass;
                if (hass?.selectedEntity) return hass.selectedEntity;
                return null;
            }
        ];

        for (const method of methods) {
            try {
                const entityId = method();
                if (entityId && typeof entityId === 'string' && entityId.includes('.')) {
                    console.log(`Entity Notes: Found entity ID: ${entityId}`);
                    return entityId;
                }
            } catch (e) {
                // Continue to next method
            }
        }

        console.log('Entity Notes: Could not determine entity ID, using unknown');
        return 'unknown';
    }

    // Inject notes into dialog
    function injectNotes(dialog, retryCount = 0) {
        const entityId = extractEntityId(dialog);
        console.log(`Entity Notes: Final entity ID: ${entityId}`);

        // Check if we already processed this dialog/entity combination
        const dialogKey = `${dialog}_${entityId}`;
        if (processedDialogs.has(dialogKey)) {
            console.log('Entity Notes: Dialog already processed, skipping');
            return;
        }

        // Find the dialog content area
        const dialogShadow = dialog.shadowRoot;
        console.log('Entity Notes: Dialog shadow root found:', !!dialogShadow);
        if (!dialogShadow) {
            console.log('Entity Notes: No dialog shadow root found');
            if (retryCount < 3) {
                console.log(`Entity Notes: Retrying in 100ms (attempt ${retryCount + 1})`);
                setTimeout(() => injectNotes(dialog, retryCount + 1), 100);
            }
            return;
        }

        const haDialog = dialogShadow.querySelector('HA-DIALOG');
        console.log('Entity Notes: HA-DIALOG found:', !!haDialog);
        if (!haDialog) {
            console.log('Entity Notes: No HA-DIALOG found');
            if (retryCount < 3) {
                console.log(`Entity Notes: Retrying in 100ms (attempt ${retryCount + 1})`);
                setTimeout(() => injectNotes(dialog, retryCount + 1), 100);
            }
            return;
        }

        // Look for content area
        const contentSelectors = ['.content', '[slot="content"]', '.mdc-dialog__content', '.dialog-content'];
        let container = null;

        for (const selector of contentSelectors) {
            container = haDialog.querySelector(selector);
            if (container) break;
        }

        if (!container) {
            // Use the ha-dialog itself as container
            container = haDialog;
        }

        console.log(`Entity Notes: Using container: ${container.tagName}`);

        // Check for existing notes card
        if (container.querySelector('entity-notes-card')) {
            console.log('Entity Notes: Notes card already exists in container');
            return;
        }

        // Create and inject notes card
        const notesCard = document.createElement('entity-notes-card');
        notesCard.setAttribute('entity-id', entityId);
        // Force the entity ID to be set before connecting
        notesCard.entityId = entityId;
        container.appendChild(notesCard);

        // Mark as processed
        processedDialogs.set(dialogKey, true);

        console.log(`Entity Notes: Injecting notes for entity: ${entityId}`);
        console.log('Entity Notes: Notes card injected successfully into content area!');
    }

    // Check for dialogs
    function checkForDialogs() {
        const homeAssistant = document.querySelector('home-assistant');
        if (!homeAssistant?.shadowRoot) return;

        const moreInfoDialog = homeAssistant.shadowRoot.querySelector('ha-more-info-dialog');
        if (moreInfoDialog) {
            console.log('Entity Notes: Found more-info dialog:');
            injectNotes(moreInfoDialog);
        }
    }

    // Setup observer
    function setupObserver() {
        console.log('Entity Notes: Setting up dialog observer...');
        
        const homeAssistant = document.querySelector('home-assistant');
        if (!homeAssistant?.shadowRoot) {
            setTimeout(setupObserver, 1000);
            return;
        }

        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'childList') {
                    checkForDialogs();
                }
            }
        });

        observer.observe(homeAssistant.shadowRoot, {
            childList: true,
            subtree: true
        });

        console.log('Entity Notes: Observer set up successfully');
        
        // Initial check
        checkForDialogs();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupObserver);
    } else {
        setupObserver();
    }

})();
