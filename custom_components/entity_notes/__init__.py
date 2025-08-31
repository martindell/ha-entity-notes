"""
Entity Notes – serve the frontend JS without blocking the event loop.
"""
from __future__ import annotations

from functools import partial
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant


async def async_setup(hass: HomeAssistant, _config) -> bool:
    """Set up the integration and register the JS endpoint."""
    hass.http.register_view(EntityNotesJSView())
    return True


class EntityNotesJSView(HomeAssistantView):
    """HTTP view to serve the entity-notes frontend script."""

    url = "/entity-notes.js"          # what the browser will request
    name = "entity_notes:js"
    requires_auth = False

    async def get(self, request):
        """Return the JS file (read safely off the event loop)."""
        hass: HomeAssistant = request.app["hass"]
        js_file_path = Path(__file__).parent / "entity-notes.js"

        # Read the file in the executor to avoid 'blocking open() in event loop'
        content = await hass.async_add_executor_job(
            partial(js_file_path.read_text, encoding="utf-8")
        )

        return web.Response(text=content, content_type="application/javascript")
