"""Property-based tests for WebSocket types and utilities.

**Feature: api-architecture-analysis, Task 3.2: WebSocket Support with typed messages**
**Validates: Requirements 4.5**
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.adapters.api.websocket.types import (
    ConnectionManager,
    ErrorMessage,
    MessageType,
    SystemMessage,
    WebSocketConnection,
    WebSocketMessage,
)


# =============================================================================
# Strategies
# =============================================================================


@st.composite
def message_types(draw: st.DrawFn) -> str:
    """Generate valid message types."""
    return draw(
        st.sampled_from(
            ["message", "chat", "notification", "system", "error", "custom"]
        )
    )


@st.composite
def client_ids(draw: st.DrawFn) -> str:
    """Generate valid client IDs."""
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        )
    )


@st.composite
def room_names(draw: st.DrawFn) -> str:
    """Generate valid room names."""
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=1,
            max_size=30,
        )
    )


# =============================================================================
# Property 1: Message Serialization Round-Trip
# =============================================================================


@given(msg_type=message_types())
@settings(max_examples=100)
def test_message_serialization_round_trip(msg_type: str) -> None:
    """Property: serialize then deserialize returns equivalent message.

    **Feature: api-architecture-analysis, Property 1: Message Round-Trip**
    **Validates: Requirements 4.5**

    For any WebSocket message, serializing to JSON and deserializing
    should produce an equivalent message.
    """
    original = WebSocketMessage(type=msg_type)
    json_str = original.to_json()
    restored = WebSocketMessage.from_json(json_str)

    assert restored.type == original.type
    assert isinstance(restored.timestamp, datetime)


@given(
    code=st.text(min_size=1, max_size=20),
    message=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100)
def test_error_message_round_trip(code: str, message: str) -> None:
    """Property: ErrorMessage serialization preserves all fields.

    **Feature: api-architecture-analysis, Property 2: Error Message Round-Trip**
    **Validates: Requirements 4.5**
    """
    original = ErrorMessage(code=code, message=message)
    json_str = original.to_json()
    restored = ErrorMessage.from_json(json_str)

    assert restored.code == original.code
    assert restored.message == original.message
    assert restored.type == "error"


@given(event=st.text(min_size=1, max_size=30))
@settings(max_examples=100)
def test_system_message_round_trip(event: str) -> None:
    """Property: SystemMessage serialization preserves event field.

    **Feature: api-architecture-analysis, Property 3: System Message Round-Trip**
    **Validates: Requirements 4.5**
    """
    original = SystemMessage(event=event)
    json_str = original.to_json()
    restored = SystemMessage.from_json(json_str)

    assert restored.event == original.event
    assert restored.type == "system"


# =============================================================================
# Property 2: Connection Manager Invariants
# =============================================================================


@given(client_ids=st.lists(client_ids(), min_size=0, max_size=20, unique=True))
@settings(max_examples=100)
def test_connection_count_matches_connected_clients(
    client_ids: list[str],
) -> None:
    """Property: connection_count equals number of connected clients.

    **Feature: api-architecture-analysis, Property 4: Connection Count**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Simulate connections (without actual WebSocket)
    for client_id in client_ids:
        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            client_id=client_id,
        )
        manager._connections[client_id] = connection

    assert manager.connection_count == len(client_ids)


@given(
    client_ids=st.lists(client_ids(), min_size=1, max_size=10, unique=True),
    disconnect_indices=st.lists(
        st.integers(min_value=0, max_value=9), min_size=0, max_size=5
    ),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_disconnect_removes_client(
    client_ids: list[str], disconnect_indices: list[int]
) -> None:
    """Property: disconnect removes client from manager.

    **Feature: api-architecture-analysis, Property 5: Disconnect Removes Client**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connections
    for client_id in client_ids:
        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            client_id=client_id,
        )
        manager._connections[client_id] = connection

    # Disconnect some clients
    disconnected = set()
    for idx in disconnect_indices:
        if idx < len(client_ids):
            client_id = client_ids[idx]
            await manager.disconnect(client_id)
            disconnected.add(client_id)

    # Verify disconnected clients are removed
    for client_id in disconnected:
        assert manager.get_connection(client_id) is None

    # Verify remaining clients are still connected
    remaining = set(client_ids) - disconnected
    assert manager.connection_count == len(remaining)


# =============================================================================
# Property 3: Room Management
# =============================================================================


@given(
    client_id=client_ids(),
    rooms=st.lists(room_names(), min_size=1, max_size=5, unique=True),
)
@settings(max_examples=100)
def test_join_room_adds_client_to_room(
    client_id: str, rooms: list[str]
) -> None:
    """Property: join_room adds client to room members.

    **Feature: api-architecture-analysis, Property 6: Join Room**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connection
    mock_ws = MagicMock()
    connection = WebSocketConnection(websocket=mock_ws, client_id=client_id)
    manager._connections[client_id] = connection

    # Join rooms
    for room in rooms:
        result = manager.join_room(client_id, room)
        assert result is True
        assert client_id in manager.get_room_members(room)


@given(
    client_id=client_ids(),
    room=room_names(),
)
@settings(max_examples=100)
def test_leave_room_removes_client_from_room(
    client_id: str, room: str
) -> None:
    """Property: leave_room removes client from room members.

    **Feature: api-architecture-analysis, Property 7: Leave Room**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connection and join room
    mock_ws = MagicMock()
    connection = WebSocketConnection(websocket=mock_ws, client_id=client_id)
    manager._connections[client_id] = connection
    manager.join_room(client_id, room)

    # Leave room
    result = manager.leave_room(client_id, room)
    assert result is True
    assert client_id not in manager.get_room_members(room)


@given(
    client_ids=st.lists(client_ids(), min_size=2, max_size=10, unique=True),
    room=room_names(),
)
@settings(max_examples=100)
def test_room_members_are_unique(client_ids: list[str], room: str) -> None:
    """Property: room members are unique (no duplicates).

    **Feature: api-architecture-analysis, Property 8: Room Members Unique**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connections and join same room multiple times
    for client_id in client_ids:
        mock_ws = MagicMock()
        connection = WebSocketConnection(websocket=mock_ws, client_id=client_id)
        manager._connections[client_id] = connection
        # Join multiple times
        manager.join_room(client_id, room)
        manager.join_room(client_id, room)

    members = manager.get_room_members(room)
    assert len(members) == len(set(members))


# =============================================================================
# Property 4: Broadcast Behavior
# =============================================================================


@given(
    client_ids=st.lists(client_ids(), min_size=1, max_size=10, unique=True),
    exclude_indices=st.lists(
        st.integers(min_value=0, max_value=9), min_size=0, max_size=3
    ),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_broadcast_excludes_specified_clients(
    client_ids: list[str], exclude_indices: list[int]
) -> None:
    """Property: broadcast excludes specified clients.

    **Feature: api-architecture-analysis, Property 9: Broadcast Exclusion**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connections with mock send
    send_counts: dict[str, int] = {}
    for client_id in client_ids:
        mock_ws = MagicMock()
        mock_ws.send_text = AsyncMock()
        connection = WebSocketConnection(websocket=mock_ws, client_id=client_id)
        manager._connections[client_id] = connection
        send_counts[client_id] = 0

    # Build exclude set
    exclude = set()
    for idx in exclude_indices:
        if idx < len(client_ids):
            exclude.add(client_ids[idx])

    # Broadcast
    message = WebSocketMessage(type="test")
    sent_count = await manager.broadcast(message, exclude=exclude)

    # Verify count
    expected_count = len(client_ids) - len(exclude)
    assert sent_count == expected_count


# =============================================================================
# Property 5: Message Timestamp
# =============================================================================


@given(msg_type=message_types())
@settings(max_examples=100)
def test_message_has_timestamp(msg_type: str) -> None:
    """Property: all messages have a timestamp.

    **Feature: api-architecture-analysis, Property 10: Message Timestamp**
    **Validates: Requirements 4.5**
    """
    message = WebSocketMessage(type=msg_type)

    assert message.timestamp is not None
    assert isinstance(message.timestamp, datetime)
    # Timestamp should be recent (within last minute)
    now = datetime.now(tz=timezone.utc)
    diff = (now - message.timestamp).total_seconds()
    assert diff < 60


# =============================================================================
# Property 6: Connection Metadata
# =============================================================================


@given(
    client_id=client_ids(),
    metadata_keys=st.lists(
        st.text(min_size=1, max_size=20), min_size=0, max_size=5
    ),
)
@settings(max_examples=100)
def test_connection_preserves_metadata(
    client_id: str, metadata_keys: list[str]
) -> None:
    """Property: connection preserves metadata.

    **Feature: api-architecture-analysis, Property 11: Connection Metadata**
    **Validates: Requirements 4.5**
    """
    mock_ws = MagicMock()
    metadata = {key: f"value_{i}" for i, key in enumerate(metadata_keys)}

    connection = WebSocketConnection(
        websocket=mock_ws,
        client_id=client_id,
        metadata=metadata,
    )

    assert connection.client_id == client_id
    assert connection.metadata == metadata
    for key in metadata_keys:
        assert key in connection.metadata


# =============================================================================
# Property 7: Get Connection
# =============================================================================


@given(
    existing_ids=st.lists(client_ids(), min_size=1, max_size=10, unique=True),
    query_id=client_ids(),
)
@settings(max_examples=100)
def test_get_connection_returns_correct_result(
    existing_ids: list[str], query_id: str
) -> None:
    """Property: get_connection returns connection if exists, None otherwise.

    **Feature: api-architecture-analysis, Property 12: Get Connection**
    **Validates: Requirements 4.5**
    """
    manager: ConnectionManager[WebSocketMessage] = ConnectionManager()

    # Add connections
    for client_id in existing_ids:
        mock_ws = MagicMock()
        connection = WebSocketConnection(websocket=mock_ws, client_id=client_id)
        manager._connections[client_id] = connection

    result = manager.get_connection(query_id)

    if query_id in existing_ids:
        assert result is not None
        assert result.client_id == query_id
    else:
        assert result is None
