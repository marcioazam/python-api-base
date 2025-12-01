"""Property-based tests for specification pattern.

**Feature: generic-fastapi-crud, Property 23: Specification Pattern Composition**
**Validates: Requirements 16.7**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.domain.common.specification import spec


class TestSpecificationComposition:
    """Property tests for specification pattern composition."""

    @settings(max_examples=100)
    @given(
        value=st.integers(),
        threshold_a=st.integers(),
        threshold_b=st.integers(),
    )
    def test_and_spec_requires_both(
        self, value: int, threshold_a: int, threshold_b: int
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 23: Specification Pattern Composition**

        For any two specifications A and B, A.and_spec(B) SHALL be satisfied
        only when both A and B are satisfied.
        """
        spec_a = spec(lambda x: x >= threshold_a, "gte_a")
        spec_b = spec(lambda x: x >= threshold_b, "gte_b")

        combined = spec_a.and_spec(spec_b)

        a_satisfied = value >= threshold_a
        b_satisfied = value >= threshold_b
        expected = a_satisfied and b_satisfied

        assert combined.is_satisfied_by(value) == expected

    @settings(max_examples=100)
    @given(
        value=st.integers(),
        threshold_a=st.integers(),
        threshold_b=st.integers(),
    )
    def test_or_spec_requires_either(
        self, value: int, threshold_a: int, threshold_b: int
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 23: Specification Pattern Composition**

        For any two specifications A and B, A.or_spec(B) SHALL be satisfied
        when either A or B is satisfied.
        """
        spec_a = spec(lambda x: x >= threshold_a, "gte_a")
        spec_b = spec(lambda x: x >= threshold_b, "gte_b")

        combined = spec_a.or_spec(spec_b)

        a_satisfied = value >= threshold_a
        b_satisfied = value >= threshold_b
        expected = a_satisfied or b_satisfied

        assert combined.is_satisfied_by(value) == expected

    @settings(max_examples=100)
    @given(
        value=st.integers(),
        threshold=st.integers(),
    )
    def test_not_spec_negates(self, value: int, threshold: int) -> None:
        """
        For any specification A, A.not_spec() SHALL be satisfied
        when A is NOT satisfied.
        """
        spec_a = spec(lambda x: x >= threshold, "gte")
        negated = spec_a.not_spec()

        a_satisfied = value >= threshold
        expected = not a_satisfied

        assert negated.is_satisfied_by(value) == expected

    @settings(max_examples=50)
    @given(
        value=st.integers(),
        threshold_a=st.integers(),
        threshold_b=st.integers(),
    )
    def test_operator_and_equals_and_spec(
        self, value: int, threshold_a: int, threshold_b: int
    ) -> None:
        """
        The & operator SHALL produce the same result as and_spec.
        """
        spec_a = spec(lambda x: x >= threshold_a, "gte_a")
        spec_b = spec(lambda x: x >= threshold_b, "gte_b")

        method_result = spec_a.and_spec(spec_b).is_satisfied_by(value)
        operator_result = (spec_a & spec_b).is_satisfied_by(value)

        assert method_result == operator_result

    @settings(max_examples=50)
    @given(
        value=st.integers(),
        threshold_a=st.integers(),
        threshold_b=st.integers(),
    )
    def test_operator_or_equals_or_spec(
        self, value: int, threshold_a: int, threshold_b: int
    ) -> None:
        """
        The | operator SHALL produce the same result as or_spec.
        """
        spec_a = spec(lambda x: x >= threshold_a, "gte_a")
        spec_b = spec(lambda x: x >= threshold_b, "gte_b")

        method_result = spec_a.or_spec(spec_b).is_satisfied_by(value)
        operator_result = (spec_a | spec_b).is_satisfied_by(value)

        assert method_result == operator_result

    @settings(max_examples=50)
    @given(
        value=st.integers(),
        threshold=st.integers(),
    )
    def test_operator_invert_equals_not_spec(
        self, value: int, threshold: int
    ) -> None:
        """
        The ~ operator SHALL produce the same result as not_spec.
        """
        spec_a = spec(lambda x: x >= threshold, "gte")

        method_result = spec_a.not_spec().is_satisfied_by(value)
        operator_result = (~spec_a).is_satisfied_by(value)

        assert method_result == operator_result

    @settings(max_examples=50)
    @given(
        value=st.integers(),
        threshold_a=st.integers(),
        threshold_b=st.integers(),
        threshold_c=st.integers(),
    )
    def test_complex_composition(
        self, value: int, threshold_a: int, threshold_b: int, threshold_c: int
    ) -> None:
        """
        Complex compositions SHALL evaluate correctly.
        (A AND B) OR C
        """
        spec_a = spec(lambda x: x >= threshold_a, "gte_a")
        spec_b = spec(lambda x: x >= threshold_b, "gte_b")
        spec_c = spec(lambda x: x >= threshold_c, "gte_c")

        combined = (spec_a & spec_b) | spec_c

        a_satisfied = value >= threshold_a
        b_satisfied = value >= threshold_b
        c_satisfied = value >= threshold_c
        expected = (a_satisfied and b_satisfied) or c_satisfied

        assert combined.is_satisfied_by(value) == expected

    @settings(max_examples=50)
    @given(
        value=st.integers(),
        threshold=st.integers(),
    )
    def test_double_negation(self, value: int, threshold: int) -> None:
        """
        Double negation SHALL return to original result.
        NOT(NOT(A)) == A
        """
        spec_a = spec(lambda x: x >= threshold, "gte")
        double_negated = spec_a.not_spec().not_spec()

        assert spec_a.is_satisfied_by(value) == double_negated.is_satisfied_by(value)
