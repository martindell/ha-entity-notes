# Dev Testing In Home Assistant

This workflow lets you test unreleased changes on a Home Assistant system without manually copying files through VS Code.

It assumes Home Assistant can reach GitHub from the Terminal add-on.

## First-Time Setup

Open the Home Assistant Terminal add-on and run:

```sh
cd /config
git clone https://github.com/martindell/ha-entity-notes.git ha-entity-notes-dev
chmod +x /config/ha-entity-notes-dev/scripts/ha-deploy-dev.sh
```

Deploy `main`:

```sh
/config/ha-entity-notes-dev/scripts/ha-deploy-dev.sh main
```

Restart Home Assistant or reload the Entity Notes integration, then hard-refresh the browser.

## Normal Test Cycle

On your development machine, push the branch you want to test:

```sh
git push origin your-branch-name
```

In the Home Assistant Terminal add-on, deploy that branch:

```sh
/config/ha-entity-notes-dev/scripts/ha-deploy-dev.sh your-branch-name
```

Then restart Home Assistant or reload the integration, and hard-refresh the browser.

## Test Current Branch Again

If the Home Assistant clone is already on the branch you want, run the script without a branch name:

```sh
/config/ha-entity-notes-dev/scripts/ha-deploy-dev.sh
```

The script fetches from GitHub, fast-forwards the current branch, and replaces `/config/custom_components/entity_notes` with the version from the dev checkout.

## Optional Paths

The script defaults to:

```sh
REPO_DIR=/config/ha-entity-notes-dev
TARGET_PARENT=/config/custom_components
```

Override them only if your Home Assistant paths differ:

```sh
REPO_DIR=/config/my-dev-copy TARGET_PARENT=/config/custom_components ./scripts/ha-deploy-dev.sh main
```

## Automated Regression Checks

From the repository root, run:

```sh
python -m pip install voluptuous==0.15.2
python -m unittest discover -s tests -v
node tests/test_editor.cjs
```

These lightweight tests exercise production storage functions and editor methods
with small Home Assistant/DOM fakes. They do not replace testing in Home Assistant.
Before release, check entity disable/re-enable, rename and delete; options changes;
repeated unsaved edits; over-limit toolbar insertions; and backup/restore on a test instance.

## Home Assistant Compatibility Tests

CI also installs actual Home Assistant packages in separate environments:

| Home Assistant | Python | Purpose |
| --- | --- | --- |
| 2024.12.0 | 3.12 | Advertised minimum; older two-argument storage write hook |
| 2025.12.0 | 3.13 | Newer one-argument storage write hook |

In an isolated environment with the matching Python version, install the selected
Home Assistant version and run:

```sh
python -m pip install -c tests/ha/constraints.txt homeassistant==2024.12.0
python -m unittest discover -s tests/ha -v
```

These tests import the integration and config flow and use real HA storage and
service registration. They cover disk roundtrips, malformed REST/service input,
explicit empty notes, backup/restore roundtrips and errors. Write failures are
injected at the Store I/O hook; no live configuration is touched. HTTP request
objects are small fakes, so this is not an end-to-end HTTP/browser test. The two
package versions cover both storage calling conventions, not every intervening
HA release or frontend version. Keep the existing live UI checks before release.

## Dashboard Notes Sensor

After deploying and restarting, check `sensor.entity_notes` in **Developer Tools
→ States**. Its state should count saved entity plus device notes, with text in
its `entity_notes` and `device_notes` attributes.

1. Add the Markdown card example from the README using an entity with a note.
2. Edit that note in its dialog. The card should update without a refresh, even
   when the total number of notes stays the same.
3. Test a device note with the device-card example, then delete it. The card
   should become blank. An entity with no note should also display blank text.
4. Save a note containing `{{ 1 + 1 }}`. The dashboard should show the expression
   literally, while the integration's own preview still renders it.
5. Rename a test entity: its note should move to the new ID in the sensor. Update
   the card's lookup to the new ID.
6. Reload the integration and confirm the sensor returns with the same ID and
   saved notes. If testing backup/restore, use disposable notes or take a fresh
   backup first; restored text should appear in the card automatically.

Automated HA tests cover platform setup/unload/reload, legacy strings and current
note records, mutations, failed writes, raw Jinja text and recorder exclusions.

## Save And Setup Regression Checks

Automated tests also delay a storage write across a reload, reject queued/new
writes during teardown, preserve a renamed notes sensor on duplicate setup, and
check device cleanup with the editor disabled. Frontend tests cover slow/failed
initial loads, retry, disabled write actions and standard/legacy strikethrough.

For a live frontend check, throttle the network while opening a note dialog:
Save/Delete should stay disabled until the note arrives. Block the note GET
request to check the Retry button, then unblock it and retry. Confirm the original
note appears and can be edited. Check `~~strikethrough~~` and the toolbar too.
