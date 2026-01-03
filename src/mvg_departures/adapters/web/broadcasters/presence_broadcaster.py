"""Broadcaster for presence updates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyview import is_connected
from pyview.live_socket import pub_sub_hub
from pyview.vendor.flet.pubsub import PubSub

from mvg_departures.domain.contracts.presence_broadcaster import PresenceBroadcasterProtocol

if TYPE_CHECKING:
    from pyview import LiveViewSocket

logger = logging.getLogger(__name__)


class PresenceBroadcaster(PresenceBroadcasterProtocol):
    """Broadcasts presence updates via PubSub."""

    async def _subscribe_socket_to_topics(
        self, socket: LiveViewSocket, dashboard_topic: str, global_topic: str
    ) -> None:
        """Subscribe socket to presence topics."""
        try:
            await socket.subscribe(dashboard_topic)
            await socket.subscribe(global_topic)
        except Exception as e:
            logger.warning(f"Failed to subscribe socket to presence topics: {e}", exc_info=True)

    async def _broadcast_to_dashboard_topic(
        self, dashboard_topic: str, user_id: str, local_count: int, total_count: int
    ) -> None:
        """Broadcast join message to dashboard topic."""
        dashboard_pubsub = PubSub(pub_sub_hub, dashboard_topic)
        await dashboard_pubsub.send_all_on_topic_async(
            dashboard_topic,
            {
                "user_id": user_id,
                "action": "joined",
                "local_count": local_count,
                "total_count": total_count,
            },
        )

    async def _broadcast_to_global_topic(
        self, global_topic: str, user_id: str, total_count: int
    ) -> None:
        """Broadcast join message to global topic."""
        global_pubsub = PubSub(pub_sub_hub, global_topic)
        await global_pubsub.send_all_on_topic_async(
            global_topic,
            {
                "user_id": user_id,
                "action": "joined",
                "total_count": total_count,
            },
        )

    async def broadcast_join(
        self,
        route_path: str,
        user_id: str,
        local_count: int,
        total_count: int,
        socket: LiveViewSocket | None = None,
    ) -> None:
        """Broadcast that a user joined a dashboard.

        Always broadcasts to all subscribers, regardless of socket connection state.
        The socket is only used for subscribing the joining user to topics if provided and connected.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        dashboard_topic = f"presence:{normalized_path}"
        global_topic = "presence:global"

        try:
            if socket is not None and is_connected(socket):
                await self._subscribe_socket_to_topics(socket, dashboard_topic, global_topic)

            await self._broadcast_to_dashboard_topic(
                dashboard_topic, user_id, local_count, total_count
            )
            await self._broadcast_to_global_topic(global_topic, user_id, total_count)
        except Exception as e:
            logger.error(f"Failed to broadcast/subscribe to presence topic: {e}", exc_info=True)

    async def broadcast_leave(
        self,
        route_path: str,
        user_id: str,
        local_count: int,
        total_count: int,
        socket: LiveViewSocket | None = None,  # noqa: ARG002
    ) -> None:
        """Broadcast that a user left a dashboard.

        Always broadcasts to all subscribers, regardless of socket connection state.
        The socket parameter is not used but kept for API compatibility.
        """
        normalized_path = route_path.strip("/").replace("/", ":") or "root"
        dashboard_topic = f"presence:{normalized_path}"
        global_topic = "presence:global"

        try:
            # Always broadcast to all subscribers on the topic (regardless of socket state)
            dashboard_pubsub = PubSub(pub_sub_hub, dashboard_topic)
            await dashboard_pubsub.send_all_on_topic_async(
                dashboard_topic,
                {
                    "user_id": user_id,
                    "action": "left",
                    "local_count": local_count,
                    "total_count": total_count,
                },
            )

            # Broadcast to global topic
            global_pubsub = PubSub(pub_sub_hub, global_topic)
            await global_pubsub.send_all_on_topic_async(
                global_topic,
                {
                    "user_id": user_id,
                    "action": "left",
                    "total_count": total_count,
                },
            )
        except Exception as e:
            logger.error(f"Failed to broadcast presence leave: {e}", exc_info=True)
