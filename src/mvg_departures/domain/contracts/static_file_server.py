"""Protocol for static file serving."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pyview import PyView


class StaticFileServerProtocol(Protocol):
    """Protocol for serving static files."""

    def register_routes(self, app: "PyView") -> None:
        """Register static file routes with the PyView app.

        Args:
            app: The PyView application instance.
        """
        ...
