"""Tests for PresenceBroadcaster."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mvg_departures.adapters.web.broadcasters import PresenceBroadcaster


@pytest.mark.asyncio
async def test_broadcast_join_when_connected() -> None:
    """Given a connected socket, when broadcasting join, then subscribes and broadcasts to topics."""
    broadcaster = PresenceBroadcaster()

    # Create a mock socket
    mock_socket = MagicMock()
    mock_socket.subscribe = AsyncMock()

    # Mock is_connected to return True
    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=True,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None  # Mock hub

        await broadcaster.broadcast_join(
            route_path="/test",
            user_id="user_123",
            local_count=5,
            total_count=10,
            socket=mock_socket,
        )

    # Verify subscriptions
    assert mock_socket.subscribe.call_count == 2
    mock_socket.subscribe.assert_any_call("presence:test")
    mock_socket.subscribe.assert_any_call("presence:global")

    # Verify broadcasts
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    dashboard_call = mock_dashboard_pubsub.send_all_on_topic_async.call_args
    assert dashboard_call[0][0] == "presence:test"
    assert dashboard_call[0][1]["user_id"] == "user_123"
    assert dashboard_call[0][1]["action"] == "joined"
    assert dashboard_call[0][1]["local_count"] == 5
    assert dashboard_call[0][1]["total_count"] == 10

    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1
    global_call = mock_global_pubsub.send_all_on_topic_async.call_args
    assert global_call[0][0] == "presence:global"
    assert global_call[0][1]["user_id"] == "user_123"
    assert global_call[0][1]["action"] == "joined"
    assert global_call[0][1]["total_count"] == 10
    assert "local_count" not in global_call[0][1]


@pytest.mark.asyncio
async def test_broadcast_join_when_not_connected() -> None:
    """Given a disconnected socket, when broadcasting join, then broadcasts but does not subscribe."""
    broadcaster = PresenceBroadcaster()

    mock_socket = MagicMock()
    mock_socket.subscribe = AsyncMock()

    # Mock is_connected to return False
    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=False,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None

        await broadcaster.broadcast_join(
            route_path="/test",
            user_id="user_123",
            local_count=5,
            total_count=10,
            socket=mock_socket,
        )

    # Verify no subscriptions (socket not connected)
    mock_socket.subscribe.assert_not_called()

    # But broadcasts should still happen (to notify other users)
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1


@pytest.mark.asyncio
async def test_broadcast_leave_when_connected() -> None:
    """Given a connected socket, when broadcasting leave, then broadcasts to topics."""
    broadcaster = PresenceBroadcaster()

    mock_socket = MagicMock()

    # Mock is_connected to return True
    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=True,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None

        await broadcaster.broadcast_leave(
            route_path="/test",
            user_id="user_123",
            local_count=4,
            total_count=9,
            socket=mock_socket,
        )

    # Verify broadcasts (no subscriptions for leave)
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    dashboard_call = mock_dashboard_pubsub.send_all_on_topic_async.call_args
    assert dashboard_call[0][0] == "presence:test"
    assert dashboard_call[0][1]["user_id"] == "user_123"
    assert dashboard_call[0][1]["action"] == "left"
    assert dashboard_call[0][1]["local_count"] == 4
    assert dashboard_call[0][1]["total_count"] == 9

    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1
    global_call = mock_global_pubsub.send_all_on_topic_async.call_args
    assert global_call[0][0] == "presence:global"
    assert global_call[0][1]["user_id"] == "user_123"
    assert global_call[0][1]["action"] == "left"
    assert global_call[0][1]["total_count"] == 9
    assert "local_count" not in global_call[0][1]


@pytest.mark.asyncio
async def test_broadcast_leave_when_not_connected() -> None:
    """Given a disconnected socket, when broadcasting leave, then still broadcasts to notify others."""
    broadcaster = PresenceBroadcaster()

    mock_socket = MagicMock()

    # Mock is_connected to return False
    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=False,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None

        await broadcaster.broadcast_leave(
            route_path="/test",
            user_id="user_123",
            local_count=4,
            total_count=9,
            socket=mock_socket,
        )

    # Verify broadcasts still occurred (to notify other users)
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1


@pytest.mark.asyncio
async def test_broadcast_join_normalizes_route_path() -> None:
    """Given a route path with slashes, when broadcasting, then normalizes path correctly."""
    broadcaster = PresenceBroadcaster()

    mock_socket = MagicMock()
    mock_socket.subscribe = AsyncMock()

    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=True,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_pubsub = MagicMock()
        mock_pubsub.send_all_on_topic_async = AsyncMock()
        mock_pubsub_class.return_value = mock_pubsub
        mock_hub.return_value = None

        await broadcaster.broadcast_join(
            route_path="/dashboard/test",
            user_id="user_123",
            local_count=1,
            total_count=1,
            socket=mock_socket,
        )

    # Verify normalized topic was used
    mock_socket.subscribe.assert_any_call("presence:dashboard:test")


@pytest.mark.asyncio
async def test_broadcast_join_handles_root_path() -> None:
    """Given root path, when broadcasting, then uses 'root' as normalized path."""
    broadcaster = PresenceBroadcaster()

    mock_socket = MagicMock()
    mock_socket.subscribe = AsyncMock()

    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.is_connected",
            return_value=True,
        ),
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_pubsub = MagicMock()
        mock_pubsub.send_all_on_topic_async = AsyncMock()
        mock_pubsub_class.return_value = mock_pubsub
        mock_hub.return_value = None

        await broadcaster.broadcast_join(
            route_path="/",
            user_id="user_123",
            local_count=1,
            total_count=1,
            socket=mock_socket,
        )

    # Verify 'root' topic was used
    mock_socket.subscribe.assert_any_call("presence:root")


@pytest.mark.asyncio
async def test_broadcast_join_without_socket() -> None:
    """Given no socket, when broadcasting join, then broadcasts but does not subscribe."""
    broadcaster = PresenceBroadcaster()

    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None

        await broadcaster.broadcast_join(
            route_path="/test",
            user_id="user_123",
            local_count=5,
            total_count=10,
            socket=None,
        )

    # Verify broadcasts occurred
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1


@pytest.mark.asyncio
async def test_broadcast_leave_without_socket() -> None:
    """Given no socket, when broadcasting leave, then broadcasts to notify others."""
    broadcaster = PresenceBroadcaster()

    with (
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.PubSub"
        ) as mock_pubsub_class,
        patch(
            "mvg_departures.adapters.web.broadcasters.presence_broadcaster.pub_sub_hub"
        ) as mock_hub,
    ):
        mock_dashboard_pubsub = MagicMock()
        mock_dashboard_pubsub.send_all_on_topic_async = AsyncMock()
        mock_global_pubsub = MagicMock()
        mock_global_pubsub.send_all_on_topic_async = AsyncMock()

        def pubsub_factory(hub, topic):  # noqa: ARG001
            return mock_dashboard_pubsub if "presence:test" in topic else mock_global_pubsub

        mock_pubsub_class.side_effect = pubsub_factory
        mock_hub.return_value = None

        await broadcaster.broadcast_leave(
            route_path="/test",
            user_id="user_123",
            local_count=4,
            total_count=9,
            socket=None,
        )

    # Verify broadcasts occurred
    assert mock_dashboard_pubsub.send_all_on_topic_async.call_count == 1
    assert mock_global_pubsub.send_all_on_topic_async.call_count == 1
