#!/bin/sh
set -eu

REPO_DIR="${REPO_DIR:-/config/ha-entity-notes-dev}"
TARGET_PARENT="${TARGET_PARENT:-/config/custom_components}"
COMPONENT_NAME="entity_notes"
SOURCE_DIR="${REPO_DIR}/custom_components/${COMPONENT_NAME}"
TARGET_DIR="${TARGET_PARENT}/${COMPONENT_NAME}"
BRANCH="${1:-}"

if [ ! -d "${REPO_DIR}/.git" ]; then
    echo "Repository not found at ${REPO_DIR}"
    echo "Clone it first with:"
    echo "  git clone https://github.com/martindell/ha-entity-notes.git ${REPO_DIR}"
    exit 1
fi

cd "${REPO_DIR}"

git fetch origin

if [ -n "${BRANCH}" ]; then
    if git rev-parse --verify --quiet "${BRANCH}" >/dev/null; then
        git switch "${BRANCH}"
    else
        git switch --track "origin/${BRANCH}"
    fi
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [ -z "${CURRENT_BRANCH}" ]; then
    echo "Cannot deploy from a detached HEAD. Switch to a branch first."
    exit 1
fi

git pull --ff-only origin "${CURRENT_BRANCH}"

if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Component source not found at ${SOURCE_DIR}"
    exit 1
fi

mkdir -p "${TARGET_PARENT}"

TEMP_DIR="${TARGET_PARENT}/${COMPONENT_NAME}.tmp.$$"
rm -rf "${TEMP_DIR}"
cp -R "${SOURCE_DIR}" "${TEMP_DIR}"
rm -rf "${TARGET_DIR}"
mv "${TEMP_DIR}" "${TARGET_DIR}"

echo "Deployed ${COMPONENT_NAME} from branch ${CURRENT_BRANCH} to ${TARGET_DIR}"
echo "Restart Home Assistant or reload the integration, then hard-refresh your browser."
