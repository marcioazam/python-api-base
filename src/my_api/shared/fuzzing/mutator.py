"""Input mutation and minimization.

**Feature: code-review-refactoring, Task 16.3: Refactor fuzzing.py**
**Validates: Requirements 5.3**
"""

from collections.abc import Callable

from .models import FuzzInput


class InputMutator:
    """Mutates inputs for fuzzing."""

    def __init__(self, seed: int | None = None) -> None:
        import random

        self._rng = random.Random(seed)

    def mutate(self, data: bytes) -> bytes:
        """Apply random mutation to data."""
        if not data:
            return bytes([self._rng.randint(0, 255)])
        mutation = self._rng.choice(
            [
                self._bit_flip,
                self._byte_flip,
                self._insert_byte,
                self._delete_byte,
                self._swap_bytes,
                self._duplicate_chunk,
            ]
        )
        return mutation(data)

    def _bit_flip(self, data: bytes) -> bytes:
        """Flip a random bit."""
        data_list = list(data)
        pos = self._rng.randint(0, len(data_list) - 1)
        bit = self._rng.randint(0, 7)
        data_list[pos] ^= 1 << bit
        return bytes(data_list)

    def _byte_flip(self, data: bytes) -> bytes:
        """Flip a random byte."""
        data_list = list(data)
        pos = self._rng.randint(0, len(data_list) - 1)
        data_list[pos] = self._rng.randint(0, 255)
        return bytes(data_list)

    def _insert_byte(self, data: bytes) -> bytes:
        """Insert a random byte."""
        pos = self._rng.randint(0, len(data))
        new_byte = bytes([self._rng.randint(0, 255)])
        return data[:pos] + new_byte + data[pos:]

    def _delete_byte(self, data: bytes) -> bytes:
        """Delete a random byte."""
        if len(data) <= 1:
            return data
        pos = self._rng.randint(0, len(data) - 1)
        return data[:pos] + data[pos + 1 :]

    def _swap_bytes(self, data: bytes) -> bytes:
        """Swap two random bytes."""
        if len(data) < 2:
            return data
        data_list = list(data)
        pos1 = self._rng.randint(0, len(data_list) - 1)
        pos2 = self._rng.randint(0, len(data_list) - 1)
        data_list[pos1], data_list[pos2] = data_list[pos2], data_list[pos1]
        return bytes(data_list)

    def _duplicate_chunk(self, data: bytes) -> bytes:
        """Duplicate a chunk of data."""
        if len(data) < 2:
            return data + data
        start = self._rng.randint(0, len(data) - 1)
        length = self._rng.randint(1, min(10, len(data) - start))
        chunk = data[start : start + length]
        insert_pos = self._rng.randint(0, len(data))
        return data[:insert_pos] + chunk + data[insert_pos:]


class InputMinimizer:
    """Minimizes crash-inducing inputs."""

    def __init__(self, target: Callable[[bytes], None]) -> None:
        self._target = target

    def minimize(self, crash_input: FuzzInput) -> FuzzInput:
        """Minimize input while preserving crash."""
        data = crash_input.data
        if len(data) <= 1:
            return crash_input
        minimized = self._binary_minimize(data)
        minimized = self._byte_minimize(minimized)
        return FuzzInput(data=minimized, source="minimized")

    def _binary_minimize(self, data: bytes) -> bytes:
        """Binary search minimization."""
        if len(data) <= 1:
            return data
        mid = len(data) // 2
        first_half = data[:mid]
        second_half = data[mid:]
        if self._still_crashes(first_half):
            return self._binary_minimize(first_half)
        if self._still_crashes(second_half):
            return self._binary_minimize(second_half)
        return data

    def _byte_minimize(self, data: bytes) -> bytes:
        """Remove bytes one at a time."""
        result = data
        i = 0
        while i < len(result):
            candidate = result[:i] + result[i + 1 :]
            if candidate and self._still_crashes(candidate):
                result = candidate
            else:
                i += 1
        return result

    def _still_crashes(self, data: bytes) -> bool:
        """Check if data still causes crash."""
        try:
            self._target(data)
            return False
        except Exception:
            return True
