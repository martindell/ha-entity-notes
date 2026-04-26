console.log('Entity Notes: Script loading...');

// Create global namespace with configuration from backend
window.entityNotes = {
    version: '2.0.0',
    debug: {{DEBUG_LOGGING}},
    maxNoteLength: {{MAX_NOTE_LENGTH}},
    hideButtonsWhenEmpty: {{HIDE_BUTTONS_WHEN_EMPTY}},
    hideButtonsUntilFocus: {{HIDE_BUTTONS_UNTIL_FOCUS}},
    enableDeviceNotes: {{ENABLE_DEVICE_NOTES}},
    confirmDelete: {{CONFIRM_DELETE}},
    showMarkdownToolbar: {{SHOW_MARKDOWN_TOOLBAR}},

    // Convenience methods for users
    enableDebug: function() {
        this.debug = true;
        console.log('Entity Notes: Debug mode enabled. Refresh page or open entity/device dialogs to see debug output.');
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
        this.hasExistingNote = false;
        this.isEditing = false;
        this.initialState = null;
        this.redoState = null;
        this.isPreviewVisible = false;
        this.updatedAt = null;
        this.renderedNote = null;
        debugLog('Entity Notes: EntityNotesCard constructor called');
    }

    get currentUserName() {
        try {
            if (this.hass && this.hass.user) return this.hass.user.name;
            const ha = document.querySelector('home-assistant');
            if (ha && ha.hass && ha.hass.user) {
                return ha.hass.user.name;
            }
        } catch (e) {
            debugLog('Entity Notes: Error getting user name: ' + e);
        }
        return "User";
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
                    display: flex;
                    flex-direction: column;
                }
                .entity-notes-view, .entity-notes-live-preview {
                    width: 100%;
                    min-height: 36px;
                    padding: 6px 8px;
                    border-radius: 4px;
                    font-family: inherit;
                    font-size: 14px;
                    line-height: 1.4;
                    box-sizing: border-box;
                    word-wrap: break-word;
                }
                .entity-notes-view {
                    border: 1px solid var(--divider-color, #e0e0e0);
                    background: var(--primary-background-color, white);
                    color: var(--primary-text-color, black);
                    cursor: text;
                    order: 1;
                }
                .entity-notes-view:hover {
                    border-color: var(--primary-color, #03a9f4);
                }
                .entity-notes-live-preview {
                    border: 1px dashed var(--primary-color, #03a9f4);
                    background: var(--secondary-background-color, #f5f5f5);
                    color: var(--primary-text-color, black);
                    margin-top: 8px;
                    order: 4;
                }
                .entity-notes-view a, .entity-notes-live-preview a {
                    color: var(--primary-color, #03a9f4);
                    text-decoration: underline;
                }
                .entity-notes-view a:hover, .entity-notes-live-preview a:hover {
                    color: var(--accent-color, #0288d1);
                }
                .entity-notes-view ul, .entity-notes-live-preview ul,
                .entity-notes-view ol, .entity-notes-live-preview ol {
                    margin: 4px 0;
                    padding-left: 20px;
                }
                .entity-notes-view li, .entity-notes-live-preview li {
                    margin: 2px 0;
                }
                .entity-notes-view h1, .entity-notes-live-preview h1 {
                    font-size: 1.1em;
                    font-weight: bold;
                    margin: 6px 0 2px 0;
                }
                .entity-notes-view h2, .entity-notes-live-preview h2 {
                    font-size: 1em;
                    font-weight: bold;
                    margin: 4px 0 2px 0;
                }
                .entity-notes-view hr, .entity-notes-live-preview hr {
                    border: none;
                    border-top: 1px solid var(--divider-color, #e0e0e0);
                    margin: 6px 0;
                }
                .entity-notes-view.hidden, .entity-notes-live-preview.hidden {
                    display: none;
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
                    overflow: auto;
                    box-sizing: border-box;
                    outline: none;
                    order: 3;
                }
                .entity-notes-textarea:focus {
                    border-color: var(--primary-color, #03a9f4);
                    box-shadow: 0 0 0 1px var(--primary-color, #03a9f4);
                }
                .entity-notes-textarea.hidden {
                    display: none;
                }
                .entity-notes-actions {
                    display: flex;
                    gap: 8px;
                    margin-top: 8px;
                    justify-content: flex-end;
                    transition: opacity 0.2s ease;
                    order: 6;
                }
                .entity-notes-actions.hidden {
                    display: none;
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
                .entity-notes-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 4px;
                    order: 5;
                    flex-wrap: wrap;
                }
                .entity-notes-timestamp {
                    font-size: 11px;
                    color: var(--secondary-text-color, #666);
                }
                .entity-notes-timestamp.hidden {
                    display: none;
                }
                .entity-notes-char-count {
                    font-size: 11px;
                    color: var(--secondary-text-color, #666);
                    margin-left: auto;
                }
                .entity-notes-char-count.warning {
                    color: var(--warning-color, #ff9800);
                }
                .entity-notes-char-count.error {
                    color: var(--error-color, #f44336);
                }
                .entity-notes-edit-controls {
                    display: flex;
                    justify-content: flex-start;
                    align-items: center;
                    margin-bottom: 4px;
                    order: 2;
                    flex-wrap: wrap;
                    gap: 4px;
                }
                .entity-notes-edit-controls.hidden {
                    display: none;
                }
                .entity-notes-persistent-toolbar {
                    display: flex;
                    gap: 4px;
                    align-items: center;
                }
                .entity-notes-toolbar-separator {
                    width: 1px;
                    height: 20px;
                    background-color: var(--divider-color, #e0e0e0);
                    margin: 0 2px;
                }
                .entity-notes-markdown-toolbar {
                    display: flex;
                    justify-content: flex-start;
                    align-items: center;
                    gap: 4px;
                    flex-wrap: wrap;
                }
                .entity-notes-markdown-toolbar.hidden {
                    display: none;
                }
                .entity-notes-md-button {
                    background: var(--secondary-background-color, #f5f5f5);
                    color: var(--primary-text-color, black);
                    border: 1px solid var(--divider-color, #e0e0e0);
                    border-radius: 4px;
                    padding: 2px;
                    cursor: pointer;
                    font-size: 12px;
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    line-height: 1;
                }
                .entity-notes-md-button:hover {
                    background: var(--divider-color, #e0e0e0);
                }
                .entity-notes-md-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .entity-notes-md-button b {
                    font-size: 14px;
                }
                .entity-notes-md-button i {
                    font-size: 14px;
                }
            </style>
            <div class="entity-notes-container">
                <div class="entity-notes-view"></div>
                <div class="entity-notes-edit-controls hidden">
                    <div class="entity-notes-persistent-toolbar">
                        <button class="entity-notes-md-button" data-action="toggle-preview" title="Toggle Live Preview" style="width: auto; padding: 0 8px;" disabled>Preview</button>
                    </div>
                    <div class="entity-notes-markdown-toolbar hidden">
                    <button class="entity-notes-md-button" data-action="undo" title="Undo (Ctrl+Z)" disabled>↩</button>
                    <button class="entity-notes-md-button" data-action="redo" title="Redo (Ctrl+Y)" disabled>↪</button>
                    <div class="entity-notes-toolbar-separator"></div>
                    <button class="entity-notes-md-button" data-format="h1" title="Heading 1">H1</button>
                    <button class="entity-notes-md-button" data-format="h2" title="Heading 2">H2</button>
                    <button class="entity-notes-md-button" data-format="bold" title="Bold"><b>B</b></button>
                    <button class="entity-notes-md-button" data-format="italic" title="Italic"><i>I</i></button>
                    <button class="entity-notes-md-button" data-format="ul" title="Bullet list">&bull;</button>
                    <button class="entity-notes-md-button" data-format="ol" title="Numbered list">1.</button>
                    <button class="entity-notes-md-button" data-format="hr" title="Divider">&mdash;</button>
                    <div class="entity-notes-toolbar-separator"></div>
                    <button class="entity-notes-md-button" data-format="inline-code" title="Inline Code">\`</button>
                    <button class="entity-notes-md-button" data-format="code-block" title="Code Block">\`\`\`</button>
                    <button class="entity-notes-md-button" data-format="link" title="Insert Link">🔗</button>
                    <button class="entity-notes-md-button" data-format="blockquote" title="Blockquote">”</button>
                    <button class="entity-notes-md-button" data-format="strikethrough" title="Strikethrough">~</button>
                </div>
                </div>
                <textarea
                    class="entity-notes-textarea"
                    placeholder="Notes (# H1, ## H2, **bold**, *italic*, - bullets, 1. numbered, --- divider, \`inline code\`, > blockquote, ~strikethrough~)"
                    maxlength="${maxLength}"
                    rows="1"
                ></textarea>
                <div class="entity-notes-live-preview hidden"></div>
                <div class="entity-notes-footer">
                    <div class="entity-notes-timestamp hidden"></div>
                    <div class="entity-notes-char-count">0/${maxLength}</div>
                </div>
                <div class="entity-notes-actions">
                    <button class="entity-notes-button entity-notes-delete">DELETE</button>
                    <button class="entity-notes-button entity-notes-save">SAVE</button>
                </div>
            </div>
        `;
    }

    renderMarkdown(text) {
        const escapeHtml = (str) => str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');

        // Single-pass inline processor: finds the earliest pattern match,
        // escapes the literal text before it, renders the match, then continues.
        const processInline = (raw) => {
            const inlinePatterns = [
                { re: /\[(.*?)\]\((.*?)\)/, render: (m) => `<a href="${escapeHtml(m[2])}" target="_blank" rel="noopener noreferrer">${escapeHtml(m[1])}</a>` }, // text
                { re: /\*\*(.+?)\*\*/, render: (m) => `<strong>${escapeHtml(m[1])}</strong>` },
                { re: /\*(.+?)\*/,     render: (m) => `<em>${escapeHtml(m[1])}</em>` },
                { re: /`(.+?)`/,       render: (m) => `<code>${escapeHtml(m[1])}</code>` }, // Inline code
                { re: /~(.+?)~/,       render: (m) => `<del>${escapeHtml(m[1])}</del>` }, // Strikethrough
                { re: /https?:\/\/[^\s]+/, render: (m) => `<a href="${escapeHtml(m[0])}" target="_blank" rel="noopener noreferrer">${escapeHtml(m[0])}</a>` },
            ];

            let result = '';
            let remaining = raw;

            while (remaining.length > 0) {
                let best = null, bestIndex = Infinity, bestPattern = null;
                for (const p of inlinePatterns) {
                    const m = p.re.exec(remaining);
                    if (m && m.index < bestIndex) {
                        best = m; bestIndex = m.index; bestPattern = p;
                    }
                }

                if (!best) {
                    result += escapeHtml(remaining);
                    break;
                }

                result += escapeHtml(remaining.slice(0, bestIndex));
                result += bestPattern.render(best);
                remaining = remaining.slice(bestIndex + best[0].length);
            }

            return result;
        };

        // Process block-level structure line by line
        const lines = text.split('\n');
        const parts = [];
        let listType = null;
        let inCodeBlock = false; // New state for code blocks
        let inBlockquote = false; // New state for blockquotes

        const flushList = () => {
            if (listType) {
                parts.push(`</${listType}>`);
                listType = null;
            }
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();

            // Handle fenced code blocks
            if (trimmed.startsWith('```')) {
                flushList();
                if (inCodeBlock) {
                    parts.push('</code></pre>');
                    inCodeBlock = false;
                } else {
                    parts.push('<pre><code>');
                    inCodeBlock = true;
                }
                continue; // Skip further processing for fence lines
            }

            if (inCodeBlock) {
                parts.push(escapeHtml(line) + '\n'); // Render content inside code block as-is, preserving newlines
                continue;
            }

            const h1Match = /^#\s+(.+)$/.exec(trimmed);
            const h2Match = /^##\s+(.+)$/.exec(trimmed);
            const ulMatch = /^[-*]\s+(.+)$/.exec(trimmed);
            const olMatch = /^\d+\.\s+(.+)$/.exec(trimmed);
            const hrMatch = /^-{3,}$/.test(trimmed);

            const blockquoteMatch = /^>\s*(.*)$/.exec(line); // Use 'line' not 'trimmed' to preserve leading spaces for blockquote content

            if (blockquoteMatch) {
                flushList();
                if (!inBlockquote) {
                    parts.push('<blockquote>');
                    inBlockquote = true;
                }
                parts.push(`<p>${processInline(blockquoteMatch[1])}</p>`);
            } else if (h2Match) {
                flushList();
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                parts.push(`<h2>${processInline(h2Match[1])}</h2>`);
            } else if (h1Match) {
                flushList();
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                parts.push(`<h1>${processInline(h1Match[1])}</h1>`);
            } else if (hrMatch) {
                flushList();
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                parts.push('<hr>');
            } else if (ulMatch) {
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                if (listType !== 'ul') { flushList(); parts.push('<ul>'); listType = 'ul'; } // Flush list if type changes
                parts.push(`<li>${processInline(ulMatch[1])}</li>`);
            } else if (olMatch) {
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                if (listType !== 'ol') { flushList(); parts.push('<ol>'); listType = 'ol'; } // Flush list if type changes
                parts.push(`<li>${processInline(olMatch[1])}</li>`);
            } else {
                flushList();
                if (inBlockquote) { parts.push('</blockquote>'); inBlockquote = false; }
                if (trimmed === '') {
                    if (i < lines.length - 1) parts.push('<br>');
                } else {
                    const isLast = i === lines.length - 1;
                    parts.push(processInline(trimmed) + (isLast ? '' : '<br>'));
                }
            }
        }

        flushList();
        if (inBlockquote) {
            parts.push('</blockquote>');
            inBlockquote = false;
        }
        return parts.join('');
    }

    updateUndoRedoButtons() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const undoBtn = this.shadowRoot.querySelector('[data-action="undo"]');
        const redoBtn = this.shadowRoot.querySelector('[data-action="redo"]');
        const previewBtn = this.shadowRoot.querySelector('[data-action="toggle-preview"]');

        if (undoBtn) undoBtn.disabled = textarea.value === this.initialState;
        if (redoBtn) redoBtn.disabled = this.redoState === null;

        if (previewBtn) {
            const isEmpty = textarea.value.trim().length === 0;
            previewBtn.disabled = isEmpty;
            
            if (isEmpty && this.isPreviewVisible) {
                this.togglePreview();
            }
        }
    }

    undo() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        if (textarea.value !== this.initialState) {
            this.redoState = textarea.value; // Save current state for redo
            textarea.value = this.initialState;
            this.updateUndoRedoButtons();
            this.triggerInputEvent(textarea);
            debugLog('Entity Notes: Performed undo.');
        }
    }

    redo() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        if (this.redoState !== null) {
            textarea.value = this.redoState;
            this.redoState = null;
            this.updateUndoRedoButtons();
            this.triggerInputEvent(textarea);
            debugLog('Entity Notes: Performed redo.');
        }
    }

    triggerInputEvent(element) {
        // Trigger input event to update char count, resize, etc.
        element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    }

    formatTimestamp(unixTimestamp) {
        if (!unixTimestamp) return '';
        const date = new Date(unixTimestamp * 1000);
        const formatter = new Intl.DateTimeFormat(navigator.language || 'en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        return formatter.format(date);
    }

    updateTimestampDisplay() {
        const tsDiv = this.shadowRoot.querySelector('.entity-notes-timestamp');
        if (this.updatedAt) {
            tsDiv.textContent = `🕒 ${this.formatTimestamp(this.updatedAt)}`;
            tsDiv.classList.remove('hidden');
        } else {
            tsDiv.classList.add('hidden');
        }
    }

    formatText(format) {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);

        let newCursorPos = -1;

        switch (format) {
            case 'h1':
            case 'h2':
            case 'ul':
            case 'ol': {
                const lineStartPos = textarea.value.lastIndexOf('\n', start - 1) + 1;

                // Find end of the line containing the selection end
                let lineEndPos = textarea.value.indexOf('\n', end);
                if (lineEndPos === -1) {
                    lineEndPos = textarea.value.length;
                }
                // If selection ends on a newline, we should not include the next line in the block.
                if (end > 0 && textarea.value[end - 1] === '\n' && end > lineStartPos) {
                    lineEndPos = end - 1;
                }

                const originalBlock = textarea.value.substring(lineStartPos, lineEndPos);
                const lines = originalBlock.split('\n');
                let newBlock;

                const prefix = { h1: '# ', h2: '## ', ul: '- ' }[format];
                const otherPrefixesRegex = /^(# |## |- |\d+\. )/;

                if (format === 'ol') {
                    // Check if all non-empty lines are already numbered
                    const allAreNumbered = lines.filter(l => l.trim() !== '').every(l => /^\d+\.\s/.test(l));
                    if (allAreNumbered) {
                        // If so, remove numbering
                        newBlock = lines.map(l => l.replace(/^\d+\.\s/, '')).join('\n');
                    } else {
                        // Otherwise, add numbering
                        let counter = 1;
                        newBlock = lines.map(l => {
                            if (l.trim() === '') return l; // Keep empty lines
                            return `${counter++}. ${l.replace(otherPrefixesRegex, '')}`;
                        }).join('\n');
                    }
                } else { // h1, h2, ul
                    // Check if all non-empty lines have the prefix
                    const allHavePrefix = lines.filter(l => l.trim() !== '').every(l => l.startsWith(prefix));
                    if (allHavePrefix) {
                        // If so, remove prefix
                        newBlock = lines.map(l => l.startsWith(prefix) ? l.substring(prefix.length) : l).join('\n');
                    } else {
                        // Otherwise, add prefix (and remove any other)
                        newBlock = lines.map(l => {
                            if (l.trim() === '') return l; // Keep empty lines
                            return prefix + l.replace(otherPrefixesRegex, '');
                        }).join('\n');
                    }
                }

                textarea.setRangeText(newBlock, lineStartPos, lineEndPos);
                
                // Adjust selection to cover the new block
                const newEnd = lineStartPos + newBlock.length;
                textarea.setSelectionRange(lineStartPos, newEnd);
                break;
            }
            case 'bold':
            case 'italic': {
                const markers = { bold: '**', italic: '*' };
                const marker = markers[format];
                const replacement = marker + selectedText + marker;
                textarea.setRangeText(replacement, start, end, 'select');

                // Adjust cursor if no text was selected
                if (start === end) {
                    textarea.setSelectionRange(start + marker.length, start + marker.length);
                }
                break;
            }
            case 'hr': {
                const value = textarea.value;
                const textBefore = value.substring(0, start);
                const needsNewlineBefore = start > 0 && textBefore.trim().length > 0 && !textBefore.endsWith('\n\n');
                const prefixNewline = needsNewlineBefore ? (textBefore.endsWith('\n') ? '\n' : '\n\n') : '';

                const textToInsert = prefixNewline + '---\n';
                textarea.setRangeText(textToInsert, start, end);
                newCursorPos = start + textToInsert.length;
                break;
            }
            case 'inline-code': {
                const marker = '`';
                const replacement = marker + selectedText + marker;
                textarea.setRangeText(replacement, start, end, 'select');
                if (start === end) {
                    textarea.setSelectionRange(start + marker.length, start + marker.length);
                }
                break;
            }
            case 'code-block': {
                const marker = '```\n';
                const closingMarker = '\n```';
                let textToInsert;
                let newCursorPos;

                if (selectedText) {
                    textToInsert = marker + selectedText + closingMarker;
                    newCursorPos = start + marker.length; // Cursor at start of selected text in block
                } else {
                    textToInsert = marker + '\n' + closingMarker;
                    newCursorPos = start + marker.length + 1; // Cursor on the empty line inside the block
                }

                textarea.setRangeText(textToInsert, start, end, 'end');
                textarea.setSelectionRange(newCursorPos, newCursorPos);
                break;
            }
            case 'link': {
                const linkText = prompt('Enter link text:', selectedText || '');
                if (linkText === null) break; // User cancelled
                const url = prompt('Enter URL:', 'https://');
                if (url === null) break; // User cancelled
                
                const linkMarkdown = `[${linkText}](${url})`;
                
                textarea.setRangeText(linkMarkdown, start, end, 'end');
                newCursorPos = start + linkMarkdown.length; // Cursor after the closing parenthesis
                textarea.setSelectionRange(newCursorPos, newCursorPos);
                break;
            }
            case 'blockquote': {
                const lineStartPos = textarea.value.lastIndexOf('\n', start - 1) + 1;
                let lineEndPos = textarea.value.indexOf('\n', end);
                if (lineEndPos === -1) {
                    lineEndPos = textarea.value.length;
                }
                if (end > 0 && textarea.value[end - 1] === '\n' && end > lineStartPos) {
                    lineEndPos = end - 1;
                }

                const originalBlock = textarea.value.substring(lineStartPos, lineEndPos);
                const lines = originalBlock.split('\n');
                const newBlock = lines.map(l => {
                    if (l.startsWith('> ')) {
                        return l.substring(2); // Remove blockquote
                    } else {
                        return '> ' + l; // Add blockquote
                    }
                }).join('\n');

                textarea.setRangeText(newBlock, lineStartPos, lineEndPos);
                const newEnd = lineStartPos + newBlock.length;
                textarea.setSelectionRange(lineStartPos, newEnd);
                break;
            }
            case 'strikethrough': {
                const marker = '~';
                const replacement = marker + selectedText + marker;
                textarea.setRangeText(replacement, start, end, 'select');
                if (start === end) {
                    textarea.setSelectionRange(start + marker.length, start + marker.length);
                }
                break;
            }
        }

        textarea.focus();
        if (newCursorPos !== -1) {
            textarea.setSelectionRange(newCursorPos, newCursorPos);
        }

        // Trigger input event to update char count etc.
        textarea.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    }

    setupEventListeners() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const viewDiv = this.shadowRoot.querySelector('.entity-notes-view');
        const charCount = this.shadowRoot.querySelector('.entity-notes-char-count');
        const saveBtn = this.shadowRoot.querySelector('.entity-notes-save');
        const deleteBtn = this.shadowRoot.querySelector('.entity-notes-delete');
            const editControls = this.shadowRoot.querySelector('.entity-notes-edit-controls');
        const markdownToolbar = this.shadowRoot.querySelector('.entity-notes-markdown-toolbar');

            editControls.addEventListener('mousedown', (event) => {
            const button = event.target.closest('.entity-notes-md-button');
            if (button) {
                event.preventDefault(); // Prevent textarea from losing focus
            }
        });

            editControls.addEventListener('click', (event) => {
            const button = event.target.closest('.entity-notes-md-button');
            if (!button) return;

            if (button.dataset.format) {
                this.formatText(button.dataset.format);
            } else if (button.dataset.action === 'undo') {
                this.undo();
            } else if (button.dataset.action === 'redo') {
                this.redo();
                } else if (button.dataset.action === 'toggle-preview') {
                    this.togglePreview();
            }
        });

        textarea.addEventListener('input', () => {
            this.updateCharCount();
            this.autoResize();
            this.updateButtonVisibility();
            this.updateUndoRedoButtons();
                if (this.isPreviewVisible) {
                    this.updateLivePreview();
                }
        });

        textarea.addEventListener('keydown', (event) => {
            if (event.ctrlKey || event.metaKey) { // metaKey for macOS
                if (event.key.toLowerCase() === 'z') {
                    event.preventDefault();
                    this.undo();
                } else if (event.key.toLowerCase() === 'y') {
                    event.preventDefault();
                    this.redo();
                }
            }
        });

        textarea.addEventListener('focus', () => {
        this.autoResize();
        this.updateButtonVisibility();
        });

        textarea.addEventListener('blur', () => {
            // When textarea loses focus, switch back to view mode if there's content
            // Add a small delay to allow button clicks to register
            setTimeout(() => {
                if (!this.shadowRoot.activeElement) {
                this.switchToViewMode();
                }
                this.updateButtonVisibility();
            }, 200);
        });

        viewDiv.addEventListener('click', (event) => {
            // Don't switch to edit mode if clicking on a link or inside a link
            // Check if the clicked element or any parent is a link
            let element = event.target;
            while (element && element !== viewDiv) {
                if (element.tagName === 'A') {
                    event.stopPropagation();
                    return;
                }
                element = element.parentElement;
            }

            this.switchToEditMode();
        });

        saveBtn.addEventListener('click', () => this.saveNote());
        deleteBtn.addEventListener('click', () => this.deleteNote());
    }

        togglePreview() {
            this.isPreviewVisible = !this.isPreviewVisible;
            const previewDiv = this.shadowRoot.querySelector('.entity-notes-live-preview');
            const previewBtn = this.shadowRoot.querySelector('[data-action="toggle-preview"]');

            if (this.isPreviewVisible) {
                previewDiv.classList.remove('hidden');
                previewBtn.style.background = 'var(--primary-color, #03a9f4)';
                previewBtn.style.color = 'white';
                this.updateLivePreview();
                debugLog('Entity Notes: Live preview enabled');
            } else {
                previewDiv.classList.add('hidden');
                previewBtn.style.background = '';
                previewBtn.style.color = '';
                debugLog('Entity Notes: Live preview disabled');
            }
        }

        updateLivePreview() {
            const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
            const previewDiv = this.shadowRoot.querySelector('.entity-notes-live-preview');
            const text = textarea.value.trim();

            if (text.length === 0) {
                previewDiv.innerHTML = '<em style="color: var(--secondary-text-color, #666);">Preview (empty)</em>';
            return;
        }
        
        // If unchanged from initial state, use the already resolved Jinja2 template
        if (text === (this.initialState ? this.initialState.trim() : '') && this.renderedNote) {
            previewDiv.innerHTML = this.renderMarkdown(this.renderedNote);
            return;
        }

        // Live Jinja2 Rendering: Ask the backend to render if we detect template tags
        if (text.includes('{{') || text.includes('{%')) {
            // Immediately show unrendered text so typing doesn't feel sluggish
            previewDiv.innerHTML = this.renderMarkdown(text);
            
            // Clear any existing timeout
            if (this.previewDebounceTimer) {
                clearTimeout(this.previewDebounceTimer);
            }
            
            // Wait 500ms after the user stops typing to ping the backend
            this.previewDebounceTimer = setTimeout(async () => {
                const itemId = this.getAttribute('entity-id') || this.getAttribute('device-id');
                const type = this.getAttribute('type') || 'entity';
                
                try {
                    const response = await fetch('/api/entity_notes/render', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            note: text,
                            entity_id: type === 'entity' ? itemId : undefined,
                            device_id: type === 'device' ? itemId : undefined,
                            user_name: this.currentUserName
                        })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        // Double-check the user hasn't typed more while we were waiting
                        if (textarea.value.trim() === text) {
                            previewDiv.innerHTML = this.renderMarkdown(result.rendered_note || text);
                        }
                    }
                } catch (error) {
                    debugLog('Entity Notes: Failed to fetch live render: ' + error);
                }
            }, 500);
        } else {
            // Regular Markdown renders instantly
            previewDiv.innerHTML = this.renderMarkdown(text);
            }
        }

    updateButtonVisibility() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const actions = this.shadowRoot.querySelector('.entity-notes-actions');
        const currentText = textarea.value.trim();

        // NEW LOGIC: Check if hide-until-focus mode is enabled
        if (window.entityNotes.hideButtonsUntilFocus) {
            // In hide-until-focus mode, only show buttons when textarea has focus
            const hasFocus = document.activeElement === textarea ||
                            this.shadowRoot.activeElement === textarea;

            if (hasFocus) {
                actions.classList.remove('hidden');
                debugLog('Entity Notes: Showing buttons (textarea has focus)');
            } else {
                actions.classList.add('hidden');
                debugLog('Entity Notes: Hiding buttons (textarea lost focus)');
            }
            return; // Exit early, don't apply other visibility logic
        }

        // EXISTING LOGIC: Original hide-when-empty behavior
        if (!window.entityNotes.hideButtonsWhenEmpty) {
            debugLog('Entity Notes: Always showing buttons (hideButtonsWhenEmpty is false)');
            return;
        }

        // Show buttons if there's text OR if there's an existing note
        const shouldShowButtons = currentText.length > 0 || this.hasExistingNote;

        if (shouldShowButtons) {
            actions.classList.remove('hidden');
            debugLog('Entity Notes: Showing buttons (has text or existing note)');
        } else {
            actions.classList.add('hidden');
            debugLog('Entity Notes: Hiding buttons (no text and no existing note)');
        }
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

    switchToEditMode() {
        this.isEditing = true;
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const viewDiv = this.shadowRoot.querySelector('.entity-notes-view');
        const charCount = this.shadowRoot.querySelector('.entity-notes-char-count');
        const markdownToolbar = this.shadowRoot.querySelector('.entity-notes-markdown-toolbar');
        this.initialState = textarea.value;
        this.redoState = null;
        this.updateUndoRedoButtons();

        viewDiv.classList.add('hidden');
        textarea.classList.remove('hidden');
        charCount.style.display = 'block';
        
        const editControls = this.shadowRoot.querySelector('.entity-notes-edit-controls');
        editControls.classList.remove('hidden');
        
        if (window.entityNotes.showMarkdownToolbar === true || window.entityNotes.showMarkdownToolbar === 'true') {
            markdownToolbar.classList.remove('hidden');
        }

            if (this.isPreviewVisible) {
                this.shadowRoot.querySelector('.entity-notes-live-preview').classList.remove('hidden');
                this.updateLivePreview();
            }

        // Focus the textarea
        setTimeout(() => {
            textarea.focus();
            this.autoResize();
        }, 10);

        debugLog('Entity Notes: Switched to edit mode');
    }

    switchToViewMode() {
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const viewDiv = this.shadowRoot.querySelector('.entity-notes-view');
        const charCount = this.shadowRoot.querySelector('.entity-notes-char-count');
        const markdownToolbar = this.shadowRoot.querySelector('.entity-notes-markdown-toolbar');
        const noteText = textarea.value.trim();

        // Only switch to view mode if there's content and we're not actively editing
        if (noteText.length > 0 && this.isEditing) {
            this.isEditing = false;

            // Convert links to clickable format, use rendered Jinja2 template if unchanged
            const textToRender = (noteText === (this.initialState ? this.initialState.trim() : '') && this.renderedNote) ? this.renderedNote : noteText;
            viewDiv.innerHTML = this.renderMarkdown(textToRender);

            viewDiv.classList.remove('hidden');
            textarea.classList.add('hidden');
            charCount.style.display = 'none';
            markdownToolbar.classList.add('hidden');
                this.shadowRoot.querySelector('.entity-notes-edit-controls').classList.add('hidden');

                // Hide preview when in view mode
                const previewDiv = this.shadowRoot.querySelector('.entity-notes-live-preview');
                if (previewDiv) previewDiv.classList.add('hidden');

            debugLog('Entity Notes: Switched to view mode');
        } else if (noteText.length === 0) {
            // If empty, stay in edit mode (or show placeholder)
            this.isEditing = false;
        }
    }

    async loadNote() {
        const itemId = this.getAttribute('entity-id') || this.getAttribute('device-id');
        const type = this.getAttribute('type') || 'entity';
        const apiPath = type === 'device' ? 'device_notes' : 'entity_notes';

        debugLog(`Entity Notes: Loading note for ${type} ${itemId}`);
        if (!itemId) return;

        try {
            const userName = encodeURIComponent(this.currentUserName);
            const response = await fetch(`/api/${apiPath}/${itemId}?user=${userName}`);
            const data = await response.json();

            const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
            const viewDiv = this.shadowRoot.querySelector('.entity-notes-view');
            const markdownToolbar = this.shadowRoot.querySelector('.entity-notes-markdown-toolbar');
            const noteText = data.note || '';
            textarea.value = noteText;
            this.renderedNote = data.rendered_note || noteText;

            this.updatedAt = data.updated_at || null;
            this.updateTimestampDisplay();

            // Track if there's an existing note
            this.hasExistingNote = noteText.length > 0;

            this.initialState = noteText;
            this.redoState = null;

            this.updateCharCount();
            this.updateButtonVisibility();
            setTimeout(() => this.autoResize(), 10);

            // Show in view mode if there's a note, edit mode if empty
            if (noteText.length > 0) {
                viewDiv.innerHTML = this.renderMarkdown(this.renderedNote);
                viewDiv.classList.remove('hidden');
                textarea.classList.add('hidden');
                markdownToolbar.classList.add('hidden');
                this.shadowRoot.querySelector('.entity-notes-edit-controls').classList.add('hidden');
                this.shadowRoot.querySelector('.entity-notes-char-count').style.display = 'none';
                this.isEditing = false;
            } else {
                viewDiv.classList.add('hidden');
                textarea.classList.remove('hidden');
                
                this.shadowRoot.querySelector('.entity-notes-edit-controls').classList.remove('hidden');
                if (window.entityNotes.showMarkdownToolbar === true || window.entityNotes.showMarkdownToolbar === 'true') {
                    markdownToolbar.classList.remove('hidden');
                }
                
                this.isEditing = false;
                this.updateUndoRedoButtons();
            }

            debugLog(`Entity Notes: Note loaded for ${type}, hasExistingNote: ${this.hasExistingNote}`);

        } catch (error) {
            console.error(`Entity Notes: Error loading note for ${type}:`, error);
        }
    }

    async saveNote() {
        const itemId = this.getAttribute('entity-id') || this.getAttribute('device-id');
        const type = this.getAttribute('type') || 'entity';
        const apiPath = type === 'device' ? 'device_notes' : 'entity_notes';
        const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
        const note = textarea.value.trim();

        debugLog(`Entity Notes: Saving note for ${type} ${itemId}: ${note}`);

        try {
            const response = await fetch(`/api/${apiPath}/${itemId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    note,
                    user_name: this.currentUserName
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.updatedAt = result.updated_at || Math.floor(Date.now() / 1000);
                this.renderedNote = result.rendered_note || note;
                this.initialState = note; // Update initial state so it matches the newly saved note
                this.updateTimestampDisplay();

                // Update the existing note status
                this.hasExistingNote = note.length > 0;
                this.updateButtonVisibility();

                // Switch to view mode after saving if there's content
                if (note.length > 0) {
                    this.isEditing = true; // Set to true so switchToViewMode will work
                    this.switchToViewMode();
                }

                debugLog(`Entity Notes: Note saved successfully for ${type}, hasExistingNote: ${this.hasExistingNote}`);
            } else {
                console.error(`Entity Notes: Save failed for ${type}`);
            }
        } catch (error) {
            console.error(`Entity Notes: Error saving note for ${type}:`, error);
        }
    }

    async deleteNote() {
        const itemId = this.getAttribute('entity-id') || this.getAttribute('device-id');
        const type = this.getAttribute('type') || 'entity';
        const apiPath = type === 'device' ? 'device_notes' : 'entity_notes';

        // New confirmation logic
        if (window.entityNotes.confirmDelete === true || window.entityNotes.confirmDelete === 'true') {
            if (!confirm(`Are you sure you want to delete the note for ${type} ${itemId}?`)) {
                debugLog(`Entity Notes: Delete cancelled for ${type} ${itemId}`); // User cancelled deletion
                return;
            }
        }

        debugLog(`Entity Notes: Deleting note for ${type} ${itemId}`);

        try {
            const response = await fetch(`/api/${apiPath}/${itemId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const textarea = this.shadowRoot.querySelector('.entity-notes-textarea');
                const viewDiv = this.shadowRoot.querySelector('.entity-notes-view');
                const markdownToolbar = this.shadowRoot.querySelector('.entity-notes-markdown-toolbar');

                textarea.value = '';
                viewDiv.innerHTML = '';
                
                this.updatedAt = null;
                this.updateTimestampDisplay();
                
                // Ensure we return to empty edit mode cleanly
                viewDiv.classList.add('hidden');
                textarea.classList.remove('hidden');
                this.shadowRoot.querySelector('.entity-notes-char-count').style.display = 'block';
                this.isEditing = true;
                
                this.shadowRoot.querySelector('.entity-notes-edit-controls').classList.remove('hidden');
                if (window.entityNotes.showMarkdownToolbar === true || window.entityNotes.showMarkdownToolbar === 'true') {
                    markdownToolbar.classList.remove('hidden');
                }
                
                this.hasExistingNote = false;

                this.updateCharCount();
                this.updateButtonVisibility();
                this.updateUndoRedoButtons();
                this.autoResize();
                debugLog(`Entity Notes: Note deleted successfully for ${type}`);
            }
        } catch (error) {
            console.error(`Entity Notes: Error deleting note for ${type}:`, error);
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

function findDialogContentArea(dialog) {
    if (!dialog?.shadowRoot) return null;

    // These selectors identify the actual scrollable content body of a dialog.
    // Ordered from most-specific (new HA/WebAwesome) to legacy (MDC).
    // [slot="content"] is intentionally excluded — it matches wrapper elements
    // (e.g. ha-dialog itself), not the inner content area.
    const contentSelectors = [
        '.dialog__body',      // WebAwesome wa-dialog (HA 2026.4+)
        '[part="body"]',      // WebAwesome CSS parts
        '.body',              // ha-dialog body class
        '.body.ha-scrollbar',
        '.content-wrapper',
        '.content',           // Legacy HA
        '.mdc-dialog__content', // Legacy MDC
        '.dialog-content',
        'ha-dialog-content',
    ];

    // Recursively walk shadow roots up to maxDepth levels deep.
    // Does NOT descend into children of a matching element.
    function searchShadow(shadowRoot, depth) {
        if (!shadowRoot || depth <= 0) return null;

        for (const sel of contentSelectors) {
            try {
                const el = shadowRoot.querySelector(sel);
                if (el) {
                    debugLog('Entity Notes: Found content area (depth ' + (6 - depth) + ') with selector: ' + sel);
                    return el;
                }
            } catch (e) {}
        }

        // Recurse into shadow roots of direct and nested children
        const children = shadowRoot.querySelectorAll('*');
        for (const child of children) {
            if (child.shadowRoot) {
                const result = searchShadow(child.shadowRoot, depth - 1);
                if (result) return result;
            }
        }
        return null;
    }

    return searchShadow(dialog.shadowRoot, 6);
}

function injectNotesIntoDialog(dialog) {
    debugLog('Entity Notes: Attempting to inject notes into dialog');

    if (!dialog || !dialog.shadowRoot) {
        debugLog('Entity Notes: No dialog or shadowRoot found');
        return;
    }

    // Check if already injected (use a property flag since card may be in nested shadow root)
    const entityId = findEntityId(dialog);
    if (!entityId) {
        debugLog('Entity Notes: No entity ID found for dialog');
        return;
    }

    // Check if already injected for this specific entity
    if (dialog._entityNotesInjectedFor === entityId) {
        debugLog('Entity Notes: Notes already injected for entity: ' + entityId);
        return;
    }

    const contentArea = findDialogContentArea(dialog);

    if (!contentArea) {
        debugLog('Entity Notes: No content area found');
        return;
    }

    // Remove any stale card from a previous entity (dialog element is reused)
    const existing = contentArea.querySelector('entity-notes-card');
    if (existing) existing.remove();

    // Create and inject notes card
    const notesCard = document.createElement('entity-notes-card');
    notesCard.setAttribute('entity-id', entityId);
    contentArea.appendChild(notesCard);
    dialog._entityNotesInjectedFor = entityId;

    debugLog('Entity Notes: Notes card injected for entity: ' + entityId);

    // Load the note after a short delay
    setTimeout(() => {
        notesCard.loadNote();
    }, 100);
}

function findDeviceId(dialog) {
    debugLog('Entity Notes: Finding device ID for dialog');

    // Try multiple methods to get device ID
    const methods = [
        () => dialog._params?.device?.id,
        () => dialog._params?.deviceId,
        () => dialog.device?.id,
        () => dialog.deviceId,
        () => dialog.getAttribute?.('device-id'),
        () => dialog.dataset?.deviceId,
        () => {
            // Try to find device ID in dialog content
            const content = dialog.shadowRoot?.querySelector('.content');
            if (content) {
                const deviceInfo = content.querySelector('[device-id]');
                return deviceInfo?.getAttribute('device-id');
            }
        }
    ];

    for (const method of methods) {
        try {
            const deviceId = method();
            if (deviceId) {
                debugLog('Entity Notes: Found device ID: ' + deviceId);
                return deviceId;
            }
        } catch (e) {
            // Continue to next method
        }
    }

    debugLog('Entity Notes: No device ID found');
    return null;
}

function injectNotesIntoDeviceDialog(dialog) {
    if (!window.entityNotes.enableDeviceNotes) {
        debugLog('Entity Notes: Device notes disabled in config');
        return;
    }

    debugLog('Entity Notes: Attempting to inject notes into device dialog');

    if (!dialog || !dialog.shadowRoot) {
        debugLog('Entity Notes: No device dialog or shadowRoot found');
        return;
    }

    const deviceId = findDeviceId(dialog);
    if (!deviceId) {
        debugLog('Entity Notes: No device ID found for dialog');
        return;
    }

    // For DIALOG-DEVICE-REGISTRY-DETAIL, we need to look inside the nested HA-DIALOG
    let targetDialog = dialog;
    if (dialog.tagName === 'DIALOG-DEVICE-REGISTRY-DETAIL') {
        const nestedDialog = dialog.shadowRoot.querySelector('ha-dialog');
        if (nestedDialog) {
            debugLog('Entity Notes: Found nested HA-DIALOG in DIALOG-DEVICE-REGISTRY-DETAIL');
            targetDialog = nestedDialog;
        }
    }

    // Check if already injected (use property flag since card may be in nested shadow root)
    if (dialog._entityNotesDeviceInjected) {
        debugLog('Entity Notes: Device notes already injected');
        return;
    }

    const contentArea = findDialogContentArea(targetDialog) ||
        // Fallback: also try the light DOM of targetDialog (no shadow root)
        (() => {
            const selectors = ['.content', '.mdc-dialog__content', '[slot="content"]', '.dialog-content', 'ha-dialog-content', '.body'];
            for (const s of selectors) {
                const el = targetDialog.querySelector?.(s);
                if (el) {
                    debugLog('Entity Notes: Found device dialog content area (light DOM) with selector: ' + s);
                    return el;
                }
            }
            return null;
        })();

    if (!contentArea) {
        debugLog('Entity Notes: No content area found in device dialog');
        if (window.entityNotes.debug) {
            debugLog('Entity Notes: Target dialog tag: ' + targetDialog.tagName);
            if (targetDialog.shadowRoot) {
                debugLog('Entity Notes: Target dialog shadowRoot children: ' + Array.from(targetDialog.shadowRoot.children).map(c => c.tagName).join(', '));
            }
        }
        return;
    }

    // Create and inject notes card
    const notesCard = document.createElement('entity-notes-card');
    notesCard.setAttribute('device-id', deviceId);
    notesCard.setAttribute('type', 'device');
    contentArea.appendChild(notesCard);
    dialog._entityNotesDeviceInjected = true;

    debugLog('Entity Notes: Notes card injected for device: ' + deviceId);

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

                    // Check if this is a more-info dialog (entity)
                    if (node.tagName === 'HA-MORE-INFO-DIALOG') {
                        debugLog('Entity Notes: More-info dialog detected');

                        // Try injection with multiple delays to ensure dialog is fully loaded
                        [100, 300, 600, 1000].forEach(delay => {
                            setTimeout(() => {
                                debugLog('Entity Notes: Attempting entity injection after ' + delay + 'ms delay');
                                injectNotesIntoDialog(node);
                            }, delay);
                        });
                    }

                    // Check if this is a device registry detail dialog (device settings)
                    if (window.entityNotes.enableDeviceNotes && node.tagName === 'DIALOG-DEVICE-REGISTRY-DETAIL') {
                        debugLog('Entity Notes: Device registry detail dialog detected');

                        // Try injection with multiple delays
                        [100, 300, 600, 1000].forEach(delay => {
                            setTimeout(() => {
                                debugLog('Entity Notes: Attempting device injection after ' + delay + 'ms delay');
                                injectNotesIntoDeviceDialog(node);
                            }, delay);
                        });
                    }

                    // Check if this is a device info dialog
                    if (window.entityNotes.enableDeviceNotes && node.tagName === 'HA-DIALOG') {
                        // Device dialogs are typically ha-dialog elements
                        // We need to check if they contain device info
                        debugLog('Entity Notes: HA-Dialog detected, checking if it is a device dialog');

                        // Try injection with multiple delays
                        [100, 300, 600, 1000].forEach(delay => {
                            setTimeout(() => {
                                debugLog('Entity Notes: Attempting device injection after ' + delay + 'ms delay');
                                injectNotesIntoDeviceDialog(node);
                            }, delay);
                        });
                    }

                    // Also check for nested dialogs
                    const nestedEntityDialogs = node.querySelectorAll?.('ha-more-info-dialog');
                    nestedEntityDialogs?.forEach(dialog => {
                        debugLog('Entity Notes: Found nested entity dialog');
                        [100, 300, 600].forEach(delay => {
                            setTimeout(() => injectNotesIntoDialog(dialog), delay);
                        });
                    });

                    if (window.entityNotes.enableDeviceNotes) {
                        const nestedDeviceDialogs = node.querySelectorAll?.('ha-dialog');
                        nestedDeviceDialogs?.forEach(dialog => {
                            debugLog('Entity Notes: Found nested ha-dialog');
                            [100, 300, 600].forEach(delay => {
                                setTimeout(() => injectNotesIntoDeviceDialog(dialog), delay);
                            });
                        });
                    }
                }
            });
        });
    });

    // HA 2026.4+: ha-more-info-dialog is a persistent element that is never
    // removed from the DOM. HA fires 'hass-more-info' each time a dialog opens,
    // so we listen for that instead of relying on MutationObserver node additions.
    window.addEventListener('hass-more-info', (event) => {
        debugLog('Entity Notes: hass-more-info event detected for entity: ' + event.detail?.entityId);
        const ha = document.querySelector('home-assistant');
        const dialog = ha?.shadowRoot?.querySelector('ha-more-info-dialog');
        if (!dialog) return;
        // Clear the per-entity flag so injection runs fresh for the new entity
        delete dialog._entityNotesInjectedFor;
        [200, 500, 1000, 2000].forEach(delay => {
            setTimeout(() => injectNotesIntoDialog(dialog), delay);
        });
    }, true);
    infoLog('Entity Notes: hass-more-info listener registered');

    // Observe the Home Assistant shadow root (where dialogs are actually created)
    debugLog('Entity Notes: Observing home-assistant shadow root');
    observer.observe(homeAssistant.shadowRoot, {
        childList: true,
        subtree: true
    });

    // Also check for existing dialogs in shadow root
    const existingEntityDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
    if (existingEntityDialogs.length > 0) {
        debugLog('Entity Notes: Found existing entity dialogs in shadow root: ' + existingEntityDialogs.length);
        existingEntityDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });
    }

    if (window.entityNotes.enableDeviceNotes) {
        // Check for device registry detail dialogs
        const existingDeviceRegistryDialogs = homeAssistant.shadowRoot.querySelectorAll('dialog-device-registry-detail');
        if (existingDeviceRegistryDialogs.length > 0) {
            debugLog('Entity Notes: Found existing device registry dialogs in shadow root: ' + existingDeviceRegistryDialogs.length);
            existingDeviceRegistryDialogs.forEach(dialog => {
                setTimeout(() => injectNotesIntoDeviceDialog(dialog), 100);
            });
        }

        // Check for general ha-dialog elements
        const existingDeviceDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-dialog');
        if (existingDeviceDialogs.length > 0) {
            debugLog('Entity Notes: Found existing ha-dialogs in shadow root: ' + existingDeviceDialogs.length);
            existingDeviceDialogs.forEach(dialog => {
                setTimeout(() => injectNotesIntoDeviceDialog(dialog), 100);
            });
        }
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
        const existingEntityDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-more-info-dialog');
        debugLog('Entity Notes: Found existing entity dialogs during init: ' + existingEntityDialogs.length);
        existingEntityDialogs.forEach(dialog => {
            setTimeout(() => injectNotesIntoDialog(dialog), 100);
        });

        if (window.entityNotes.enableDeviceNotes) {
            // Check for device registry detail dialogs
            const existingDeviceRegistryDialogs = homeAssistant.shadowRoot.querySelectorAll('dialog-device-registry-detail');
            debugLog('Entity Notes: Found existing device registry dialogs during init: ' + existingDeviceRegistryDialogs.length);
            existingDeviceRegistryDialogs.forEach(dialog => {
                setTimeout(() => injectNotesIntoDeviceDialog(dialog), 100);
            });

            // Check for general ha-dialog elements
            const existingDeviceDialogs = homeAssistant.shadowRoot.querySelectorAll('ha-dialog');
            debugLog('Entity Notes: Found existing device dialogs during init: ' + existingDeviceDialogs.length);
            existingDeviceDialogs.forEach(dialog => {
                setTimeout(() => injectNotesIntoDeviceDialog(dialog), 100);
            });
        }
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
        debugLog('Entity Notes: Observer found, initialization appears successful');
    }
}, 2000);

infoLog('Entity Notes: Script loaded successfully');
