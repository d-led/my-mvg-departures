"""Behavior-focused tests for StateBroadcaster."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mvg_departures.adapters.web.broadcasters.state_broadcaster import StateBroadcaster


class TestStateBroadcaster:
    """Tests for state broadcast behavior."""

    @pytest.mark.asyncio
    async def test_when_broadcast_succeeds_then_sends_update_to_topic(self) -> None:
        """Given a topic, when broadcasting, then sends update message to that topic."""
        broadcaster = StateBroadcaster()

        with patch(
            "mvg_departures.adapters.web.broadcasters.state_broadcaster.PubSub"
        ) as mock_pubsub_class:
            mock_pubsub = MagicMock()
            mock_pubsub.send_all_on_topic_async = AsyncMock()
            mock_pubsub_class.return_value = mock_pubsub

            await broadcaster.broadcast_update("test-topic")

            mock_pubsub.send_all_on_topic_async.assert_called_once_with("test-topic", "update")

    @pytest.mark.asyncio
    async def test_when_broadcast_fails_then_logs_error_and_continues(self) -> None:
        """Given PubSub error, when broadcasting, then logs error without raising."""
        broadcaster = StateBroadcaster()

        with patch(
            "mvg_departures.adapters.web.broadcasters.state_broadcaster.PubSub"
        ) as mock_pubsub_class:
            mock_pubsub = MagicMock()
            mock_pubsub.send_all_on_topic_async = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            mock_pubsub_class.return_value = mock_pubsub

            # Should not raise - error is caught and logged
            await broadcaster.broadcast_update("test-topic")

            # Verify the method was called even though it failed
            mock_pubsub.send_all_on_topic_async.assert_called_once()
