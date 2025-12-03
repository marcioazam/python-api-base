"""Property-based tests for ID generation.

**Feature: generic-fastapi-crud, Property 20: ID Generation Uniqueness and Sortability**
**Validates: Requirements 16.2**
"""

import time

from hypothesis import given, settings
from hypothesis import strategies as st

from core.shared.utils.ids import (
    generate_ulid,
    generate_uuid7,
    is_valid_ulid,
    is_valid_uuid7,
)


class TestIDGeneration:
    """Property tests for ID generation."""

    @settings(max_examples=50)
    @given(count=st.integers(min_value=2, max_value=20))
    def test_ulid_uniqueness(self, count: int) -> None:
        """
        **Feature: generic-fastapi-crud, Property 20: ID Generation Uniqueness and Sortability**

        For any sequence of generated ULIDs, each ID SHALL be unique.
        """
        ulids = [generate_ulid() for _ in range(count)]
        assert len(set(ulids)) == count, "All generated ULIDs should be unique"

    @settings(max_examples=50)
    @given(count=st.integers(min_value=2, max_value=20))
    def test_uuid7_uniqueness(self, count: int) -> None:
        """
        For any sequence of generated UUID7s, each ID SHALL be unique.
        """
        uuids = [generate_uuid7() for _ in range(count)]
        assert len(set(uuids)) == count, "All generated UUID7s should be unique"

    def test_ulid_sortability_over_time(self) -> None:
        """
        **Feature: generic-fastapi-crud, Property 20: ID Generation Uniqueness and Sortability**

        IDs generated later SHALL sort lexicographically after IDs generated earlier.
        """
        # Generate IDs with small delays to ensure different timestamps
        ulid1 = generate_ulid()
        time.sleep(0.002)  # 2ms delay
        ulid2 = generate_ulid()
        time.sleep(0.002)
        ulid3 = generate_ulid()

        # ULIDs should be lexicographically sortable by time
        assert ulid1 < ulid2 < ulid3, "ULIDs should sort by creation time"

    def test_uuid7_sortability_over_time(self) -> None:
        """
        UUID7s generated later SHALL sort lexicographically after earlier ones.
        """
        uuid1 = generate_uuid7()
        time.sleep(0.002)
        uuid2 = generate_uuid7()
        time.sleep(0.002)
        uuid3 = generate_uuid7()

        # UUID7s should be sortable by time
        assert uuid1 < uuid2 < uuid3, "UUID7s should sort by creation time"

    @settings(max_examples=30)
    @given(st.data())
    def test_generated_ulids_are_valid(self, data: st.DataObject) -> None:
        """
        For any generated ULID, is_valid_ulid SHALL return True.
        """
        ulid = generate_ulid()
        assert is_valid_ulid(ulid), f"Generated ULID {ulid} should be valid"

    @settings(max_examples=30)
    @given(st.data())
    def test_generated_uuid7s_are_valid(self, data: st.DataObject) -> None:
        """
        For any generated UUID7, is_valid_uuid7 SHALL return True.
        """
        uuid = generate_uuid7()
        assert is_valid_uuid7(uuid), f"Generated UUID7 {uuid} should be valid"

    def test_ulid_format(self) -> None:
        """ULIDs SHALL be 26 characters in Crockford Base32."""
        ulid = generate_ulid()
        assert len(ulid) == 26
        # Crockford Base32 alphabet (excluding I, L, O, U)
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        assert all(c in valid_chars for c in ulid.upper())

    def test_uuid7_format(self) -> None:
        """UUID7s SHALL be 36 characters with hyphens."""
        uuid = generate_uuid7()
        assert len(uuid) == 36
        # UUID format: 8-4-4-4-12
        parts = uuid.split("-")
        assert len(parts) == 5
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]

    @settings(max_examples=20)
    @given(
        invalid_str=st.text(min_size=0, max_size=50).filter(
            lambda x: len(x) != 26 or not x.isalnum()
        )
    )
    def test_invalid_ulid_detection(self, invalid_str: str) -> None:
        """
        For any string that is not a valid ULID format, is_valid_ulid SHALL return False.
        """
        # Skip strings that might accidentally be valid ULIDs
        if len(invalid_str) == 26 and invalid_str.isalnum():
            return
        assert not is_valid_ulid(invalid_str)

    @settings(max_examples=20)
    @given(
        invalid_str=st.text(min_size=0, max_size=50).filter(lambda x: len(x) != 36)
    )
    def test_invalid_uuid7_detection(self, invalid_str: str) -> None:
        """
        For any string that is not a valid UUID format, is_valid_uuid7 SHALL return False.
        """
        assert not is_valid_uuid7(invalid_str)
