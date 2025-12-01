"""Property-based tests for GraphQL types and utilities.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**
"""

import base64

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.adapters.api.graphql.types import (
    Connection,
    ConnectionArgs,
    Edge,
    PageInfo,
    connection_from_list,
    decode_cursor,
    encode_cursor,
)


# =============================================================================
# Strategies
# =============================================================================


@st.composite
def cursor_values(draw: st.DrawFn) -> str | int:
    """Generate valid cursor values."""
    return draw(st.one_of(
        st.integers(min_value=0, max_value=10000),
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        ),
    ))


@st.composite
def cursor_prefixes(draw: st.DrawFn) -> str:
    """Generate valid cursor prefixes."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=1,
        max_size=20,
    ))


@st.composite
def item_lists(draw: st.DrawFn) -> list[str]:
    """Generate lists of items (using strings as simple items)."""
    return draw(st.lists(
        st.text(min_size=1, max_size=50),
        min_size=0,
        max_size=100,
    ))


@st.composite
def connection_args(draw: st.DrawFn) -> ConnectionArgs:
    """Generate valid ConnectionArgs."""
    first = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=50)))
    last = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=50)))

    # Only one of first/last should be set
    if first is not None and last is not None:
        if draw(st.booleans()):
            first = None
        else:
            last = None

    return ConnectionArgs(
        first=first,
        after=None,  # Cursors tested separately
        last=last,
        before=None,
    )


# =============================================================================
# Property 1: Cursor Round-Trip
# =============================================================================


@given(value=cursor_values(), prefix=cursor_prefixes())
@settings(max_examples=100)
def test_cursor_encode_decode_round_trip(value: str | int, prefix: str) -> None:
    """Property: encode then decode returns original value.

    **Feature: api-architecture-analysis, Property 1: Cursor Round-Trip**
    **Validates: Requirements 4.5**

    For any cursor value and prefix, encoding and then decoding
    should return the original value as a string.
    """
    encoded = encode_cursor(value, prefix)
    decoded = decode_cursor(encoded, prefix)

    assert decoded == str(value)


@given(value=cursor_values())
@settings(max_examples=100)
def test_cursor_is_base64(value: str | int) -> None:
    """Property: encoded cursor is valid base64.

    **Feature: api-architecture-analysis, Property 2: Cursor Format**
    **Validates: Requirements 4.5**

    For any cursor value, the encoded cursor should be valid base64.
    """
    encoded = encode_cursor(value)

    # Should not raise
    decoded_bytes = base64.b64decode(encoded.encode())
    assert isinstance(decoded_bytes, bytes)


# =============================================================================
# Property 2: Connection Invariants
# =============================================================================


@given(items=item_lists())
@settings(max_examples=100)
def test_connection_total_count_matches(items: list[str]) -> None:
    """Property: connection total_count equals input length.

    **Feature: api-architecture-analysis, Property 3: Connection Total Count**
    **Validates: Requirements 4.5**

    For any list of items, the connection's total_count should
    equal the length of the input list.
    """
    connection = connection_from_list(items)

    assert connection.total_count == len(items)


@given(items=item_lists(), args=connection_args())
@settings(max_examples=100)
def test_connection_edges_not_exceed_first(
    items: list[str], args: ConnectionArgs
) -> None:
    """Property: edges count does not exceed 'first' argument.

    **Feature: api-architecture-analysis, Property 4: Pagination Limit**
    **Validates: Requirements 4.5**

    When 'first' is specified, the number of edges should not
    exceed that value.
    """
    connection = connection_from_list(items, args)

    if args.first is not None:
        assert len(connection.edges) <= args.first


@given(items=item_lists(), args=connection_args())
@settings(max_examples=100)
def test_connection_edges_not_exceed_last(
    items: list[str], args: ConnectionArgs
) -> None:
    """Property: edges count does not exceed 'last' argument.

    **Feature: api-architecture-analysis, Property 5: Pagination Limit (Last)**
    **Validates: Requirements 4.5**

    When 'last' is specified, the number of edges should not
    exceed that value.
    """
    connection = connection_from_list(items, args)

    if args.last is not None:
        assert len(connection.edges) <= args.last


@given(items=item_lists())
@settings(max_examples=100)
def test_connection_edges_have_unique_cursors(items: list[str]) -> None:
    """Property: all edges have unique cursors.

    **Feature: api-architecture-analysis, Property 6: Cursor Uniqueness**
    **Validates: Requirements 4.5**

    For any connection, all edge cursors should be unique.
    """
    connection = connection_from_list(items)

    cursors = [edge.cursor for edge in connection.edges]
    assert len(cursors) == len(set(cursors))


@given(items=item_lists())
@settings(max_examples=100)
def test_connection_page_info_consistency(items: list[str]) -> None:
    """Property: page_info is consistent with edges.

    **Feature: api-architecture-analysis, Property 7: PageInfo Consistency**
    **Validates: Requirements 4.5**

    For any connection:
    - If edges is empty, start_cursor and end_cursor should be None
    - If edges is not empty, start_cursor and end_cursor should be set
    """
    connection = connection_from_list(items)

    if len(connection.edges) == 0:
        assert connection.page_info.start_cursor is None
        assert connection.page_info.end_cursor is None
    else:
        assert connection.page_info.start_cursor is not None
        assert connection.page_info.end_cursor is not None
        assert connection.page_info.start_cursor == connection.edges[0].cursor
        assert connection.page_info.end_cursor == connection.edges[-1].cursor


# =============================================================================
# Property 3: Edge Structure
# =============================================================================


@given(items=item_lists())
@settings(max_examples=100)
def test_edge_nodes_match_input_items(items: list[str]) -> None:
    """Property: edge nodes contain the original items.

    **Feature: api-architecture-analysis, Property 8: Edge Node Integrity**
    **Validates: Requirements 4.5**

    For any list of items, the edge nodes should contain
    the same items in the same order.
    """
    connection = connection_from_list(items)

    nodes = [edge.node for edge in connection.edges]
    assert nodes == items


# =============================================================================
# Property 4: Pagination Behavior
# =============================================================================


@given(items=st.lists(st.text(min_size=1), min_size=5, max_size=20))
@settings(max_examples=100)
def test_first_pagination_returns_first_n_items(items: list[str]) -> None:
    """Property: first=n returns the first n items.

    **Feature: api-architecture-analysis, Property 9: First Pagination**
    **Validates: Requirements 4.5**

    When first=n is specified, the connection should return
    the first n items from the list.
    """
    n = min(3, len(items))
    args = ConnectionArgs(first=n)
    connection = connection_from_list(items, args)

    nodes = [edge.node for edge in connection.edges]
    assert nodes == items[:n]


@given(items=st.lists(st.text(min_size=1), min_size=5, max_size=20))
@settings(max_examples=100)
def test_last_pagination_returns_last_n_items(items: list[str]) -> None:
    """Property: last=n returns the last n items.

    **Feature: api-architecture-analysis, Property 10: Last Pagination**
    **Validates: Requirements 4.5**

    When last=n is specified, the connection should return
    the last n items from the list.
    """
    n = min(3, len(items))
    args = ConnectionArgs(last=n)
    connection = connection_from_list(items, args)

    nodes = [edge.node for edge in connection.edges]
    assert nodes == items[-n:]


# =============================================================================
# Property 5: has_next_page / has_previous_page
# =============================================================================


@given(items=st.lists(st.text(min_size=1), min_size=5, max_size=20))
@settings(max_examples=100)
def test_has_next_page_when_more_items_exist(items: list[str]) -> None:
    """Property: has_next_page is true when more items exist.

    **Feature: api-architecture-analysis, Property 11: Has Next Page**
    **Validates: Requirements 4.5**

    When first < total items, has_next_page should be true.
    """
    n = len(items) // 2
    if n == 0:
        return  # Skip if list too small

    args = ConnectionArgs(first=n)
    connection = connection_from_list(items, args)

    assert connection.page_info.has_next_page is True


@given(items=st.lists(st.text(min_size=1), min_size=1, max_size=20))
@settings(max_examples=100)
def test_no_has_next_page_when_all_items_returned(items: list[str]) -> None:
    """Property: has_next_page is false when all items returned.

    **Feature: api-architecture-analysis, Property 12: No Next Page**
    **Validates: Requirements 4.5**

    When all items are returned, has_next_page should be false.
    """
    connection = connection_from_list(items)

    assert connection.page_info.has_next_page is False


@given(items=st.lists(st.text(min_size=1), min_size=1, max_size=20))
@settings(max_examples=100)
def test_no_has_previous_page_at_start(items: list[str]) -> None:
    """Property: has_previous_page is false at start.

    **Feature: api-architecture-analysis, Property 13: No Previous Page**
    **Validates: Requirements 4.5**

    When starting from the beginning, has_previous_page should be false.
    """
    connection = connection_from_list(items)

    assert connection.page_info.has_previous_page is False
