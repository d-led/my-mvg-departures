"""Static file server implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from starlette.responses import FileResponse, Response
from starlette.routing import Route

from mvg_departures.domain.contracts.static_file_server import StaticFileServerProtocol

if TYPE_CHECKING:
    from pyview import PyView

logger = logging.getLogger(__name__)


class StaticFileServer(StaticFileServerProtocol):
    """Serves static files for the web application."""

    def register_routes(self, app: PyView) -> None:
        """Register static file routes with the PyView app.

        Args:
            app: The PyView application instance.
        """
        # Add route to serve pyview's client JavaScript
        app.routes.append(Route("/static/assets/app.js", self._serve_app_js))
        # Add route to serve GitHub icon
        app.routes.append(Route("/static/assets/github-mark.svg", self._serve_github_icon))

    async def _serve_app_js(self, _request: Any) -> Any:
        """Serve pyview's client JavaScript."""
        try:
            # Get pyview package path
            import pyview

            pyview_path = Path(pyview.__file__).parent
            client_js_path = pyview_path / "static" / "assets" / "app.js"

            if client_js_path.exists():
                return FileResponse(str(client_js_path), media_type="application/javascript")
            # Fallback: try alternative path
            alt_path = pyview_path / "assets" / "js" / "app.js"
            if alt_path.exists():
                return FileResponse(str(alt_path), media_type="application/javascript")
            logger.error(f"Could not find pyview client JS at {client_js_path} or {alt_path}")
            return Response(
                content="// PyView client not found",
                media_type="application/javascript",
                status_code=404,
            )
        except Exception as e:
            logger.error(f"Error serving pyview client JS: {e}", exc_info=True)
            return Response(
                content="// Error loading client",
                media_type="application/javascript",
                status_code=500,
            )

    async def _serve_github_icon(self, _request: Any) -> Any:
        """Serve GitHub octicon SVG."""
        try:
            # Try multiple possible locations for the static file
            # 1. Relative to working directory (Docker: /app/static/)
            # 2. Relative to source file (development: project_root/static/)
            possible_paths = [
                Path.cwd() / "static" / "assets" / "github-mark.svg",
                Path(__file__).parent.parent.parent.parent.parent
                / "static"
                / "assets"
                / "github-mark.svg",
            ]

            for github_icon_path in possible_paths:
                if github_icon_path.exists():
                    return FileResponse(str(github_icon_path), media_type="image/svg+xml")

            logger.error(
                f"Could not find GitHub icon at any of: {[str(p) for p in possible_paths]}"
            )
            return Response(
                content="<!-- GitHub icon not found -->",
                media_type="image/svg+xml",
                status_code=404,
            )
        except Exception as e:
            logger.error(f"Error serving GitHub icon: {e}", exc_info=True)
            return Response(
                content="<!-- Error loading icon -->",
                media_type="image/svg+xml",
                status_code=500,
            )
