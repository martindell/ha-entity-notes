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
