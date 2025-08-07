console.log('Entity Notes: Script loading...');

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

console.log('Entity Notes: Script loaded successfully');