"""Broadcaster for state updates."""

from __future__ import annotations

import logging

from pyview.live_socket import pub_sub_hub
from pyview.vendor.flet.pubsub import PubSub

from mvg_departures.domain.contracts.state_broadcaster import StateBroadcasterProtocol

logger = logging.getLogger(__name__)


class StateBroadcaster(StateBroadcasterProtocol):
    """Broadcasts state updates via PubSub."""

    async def broadcast_update(self, topic: str) -> None:
        """Broadcast an update signal to all subscribers on the topic.

        Args:
            topic: The pub/sub topic to broadcast to.
        """
        try:
            pubsub = PubSub(pub_sub_hub, topic)
            await pubsub.send_all_on_topic_async(topic, "update")
            logger.info(f"Broadcasted update via pubsub to topic: {topic}")
        except Exception as e:
            logger.error(f"Failed to broadcast via pubsub: {e}", exc_info=True)
