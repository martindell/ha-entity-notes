const fs=require('fs'),vm=require('vm'),assert=require('assert');
let source=fs.readFileSync('custom_components/entity_notes/entity-notes.js','utf8').replace(/\{\{[A-Z_]+\}\}/g,'false');
new vm.Script(source);console.log('PASS: frontend parses after configuration substitution');
source=source.slice(0,source.indexOf('// Register the custom element'))+'\nglobalThis.Card = EntityNotesCard;';
const ctx={console,window:{location:{origin:'https://ha.local'}},document:{querySelector:()=>null},HTMLElement:class{attachShadow(){this.shadowRoot={}}},setTimeout:()=>0,Event:class{},alert:()=>{}};vm.createContext(ctx);vm.runInContext(source,ctx);
function card(){const c=new ctx.Card();const els={};c.shadowRoot.querySelector=s=>els[s]??=( {value:'',innerHTML:'',style:{},classList:{add(){},remove(){},contains(){return false}},focus(){}});c.getAttribute=n=>n==='entity-id'?'sensor.test':null;for(const n of ['updateTimestampDisplay','updateCharCount','updateButtonVisibility','updateEditControlsVisibility','updateCharCountVisibility','updateUndoRedoButtons','autoResize'])c[n]=()=>{};return c;}
(async()=>{
let c=card();c.shadowRoot.querySelector('.entity-notes-textarea').value='saved A';c.initialState='saved A';c.renderedNote='saved A';c.switchToEditMode();c.shadowRoot.querySelector('.entity-notes-textarea').value='unsaved B';c.switchToViewMode();c.switchToEditMode();c.switchToViewMode();assert.equal(c.shadowRoot.querySelector('.entity-notes-view').innerHTML,'unsaved B');assert.equal(c.initialState,'saved A');console.log('PASS: repeated edit/blur preserves draft rendering and saved baseline');
c=card();ctx.window.entityNotes.hideMarkdownPlaceholder=true;ctx.window.entityNotes.emptyNotePlaceholder='Use "notes" <here>';c.render();assert(!c.shadowRoot.innerHTML.includes('placeholder="Use'));assert.equal(c.shadowRoot.querySelector('.entity-notes-textarea').placeholder,'Use "notes" <here>');console.log('PASS: custom placeholder assigned as text');
for(const x of ['<img src=x onerror=alert(1)>','[x](javascript:alert(1))']){const out=c.renderMarkdown(x);assert(!out.includes('<img'));assert(!out.includes('href="javascript:'));}console.log('PASS: note HTML and unsafe links escaped');
c=card();c.shadowRoot.querySelector('.entity-notes-textarea').value='draft';c.authenticatedFetch=async()=>({ok:true,json:async()=>({note:'canonical',rendered_note:'canonical',updated_at:123})});await c.saveNote();assert.equal(c.initialState,'canonical');assert.equal(c.shadowRoot.querySelector('.entity-notes-textarea').value,'canonical');console.log('PASS: save uses canonical server text');
c=card();c.initialState='original';c.shadowRoot.querySelector('.entity-notes-textarea').value='oversized';let message;ctx.alert=s=>message=s;c.authenticatedFetch=async()=>({ok:false,status:400,json:async()=>({error:'Note exceeds maximum length'})});await c.saveNote();assert.equal(c.initialState,'original');assert.equal(c.shadowRoot.querySelector('.entity-notes-textarea').value,'oversized');assert.equal(message,'Note exceeds maximum length');console.log('PASS: rejected save preserves draft and displays validation message');
c=card();c.initialState='original';c.renderedNote='original';ctx.window.entityNotes.confirmDelete=false;c.authenticatedFetch=async()=>({ok:true});await c.deleteNote();assert.equal(c.initialState,'');assert.equal(c.renderedNote,'');console.log('PASS: delete clears cached saved state');

// An empty rendered template is a valid result, distinct from a missing result.
c=card();c.authenticatedFetch=async()=>({ok:true,json:async()=>({note:"{{ '' }}",rendered_note:'',updated_at:123})});await c.loadNote();assert.equal(c.renderedNote,'');assert.equal(c.shadowRoot.querySelector('.entity-notes-view').innerHTML,'');c.switchToEditMode();c.switchToViewMode();assert.equal(c.shadowRoot.querySelector('.entity-notes-view').innerHTML,'');c.updateLivePreview();assert.equal(c.shadowRoot.querySelector('.entity-notes-live-preview').innerHTML,'');console.log('PASS: empty template stays empty on load, edit/blur and cached preview');
c=card();c.shadowRoot.querySelector('.entity-notes-textarea').value="{{ '' }}";c.authenticatedFetch=async()=>({ok:true,json:async()=>({note:"{{ '' }}",rendered_note:'',updated_at:123})});await c.saveNote();assert.equal(c.shadowRoot.querySelector('.entity-notes-view').innerHTML,'');console.log('PASS: saved empty template does not show source');
c=card();c.shadowRoot.querySelector('.entity-notes-textarea').value="{{ '' }}";let previewCallback;ctx.setTimeout=fn=>{previewCallback=fn;return 1;};c.authenticatedFetch=async()=>({ok:true,json:async()=>({rendered_note:''})});c.updateLivePreview();await previewCallback();assert.equal(c.shadowRoot.querySelector('.entity-notes-live-preview').innerHTML,'');ctx.setTimeout=()=>0;console.log('PASS: live preview accepts empty server rendering');
c=card();c.updatedAt=123;c.hasExistingNote=true;c.initialState='old';c.shadowRoot.querySelector('.entity-notes-textarea').value='';c.authenticatedFetch=async()=>({ok:true,json:async()=>({note:'',rendered_note:'',updated_at:null})});await c.saveNote();assert.equal(c.updatedAt,null);assert.equal(c.initialState,'');assert.equal(c.hasExistingNote,false);console.log('PASS: clearing through Save removes timestamp');

// Keep promises pending to reproduce slow responses deterministically.
for (const firstAction of ['saveNote', 'deleteNote']) {
    c=card();ctx.window.entityNotes.confirmDelete=false;
    const textarea=c.shadowRoot.querySelector('.entity-notes-textarea');
    textarea.value='original';c.initialState='original';c.isEditing=true;
    let finish,calls=0;c.authenticatedFetch=()=>{calls++;return new Promise(resolve=>finish=resolve);};
    const pending=c[firstAction]();
    assert.equal(c.shadowRoot.querySelector('.entity-notes-save').disabled,true);
    assert.equal(c.shadowRoot.querySelector('.entity-notes-delete').disabled,true);
    textarea.value='new draft';
    await c.saveNote();await c.deleteNote();assert.equal(calls,1);
    finish({ok:true,json:async()=>({note:'original',rendered_note:'original',updated_at:123})});
    await pending;
    assert.equal(textarea.value,'new draft');assert.equal(c.isEditing,true);
    assert.equal(c.writePending,false);
    assert.equal(c.shadowRoot.querySelector('.entity-notes-save').disabled,false);
    assert.equal(c.shadowRoot.querySelector('.entity-notes-delete').disabled,false);
    c.authenticatedFetch=async()=>({ok:true,json:async()=>({note:'new draft',rendered_note:'new draft',updated_at:124})});
    await c.saveNote();assert.equal(c.initialState,'new draft');
    console.log('PASS: pending '+firstAction+' blocks overlapping writes and preserves newer draft');
}
for (const action of ['saveNote','deleteNote']) {
    for (const networkFailure of [false,true]) {
        c=card();ctx.window.entityNotes.confirmDelete=false;c.initialState='saved';
        c.shadowRoot.querySelector('.entity-notes-textarea').value='draft';
        c.authenticatedFetch=async()=>{if(networkFailure)throw Error('offline');return {ok:false,status:500,json:async()=>({error:'disk full'})};};
        await c[action]();assert.equal(c.writePending,false);
        assert.equal(c.shadowRoot.querySelector('.entity-notes-save').disabled,false);
        assert.equal(c.shadowRoot.querySelector('.entity-notes-delete').disabled,false);
        assert.equal(c.shadowRoot.querySelector('.entity-notes-textarea').value,'draft');
        assert.equal(c.initialState,'saved');
    }
    console.log('PASS: '+action+' failures unlock controls and preserve draft');
}
})().catch(e=>{console.error(e);process.exitCode=1});
