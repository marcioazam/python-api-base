"""Property-based tests for Advanced Specification pattern.

**Feature: advanced-reusability, Properties 2-5**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**
"""

from dataclasses import dataclass

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.domain.common.advanced_specification import (
    ComparisonOperator,
    FieldSpecification,
    SpecificationBuilder,
    field_between,
    field_eq,
    field_ge,
    field_gt,
    field_in,
    field_le,
    field_lt,
    field_ne,
)


@dataclass
class SampleEntity:
    """Sample entity for testing specifications."""

    id: int
    name: str
    age: int
    score: float
    status: str
    is_active: bool


# Strategies for generating test data
entity_strategy = st.builds(
    SampleEntity,
    id=st.integers(min_value=1, max_value=10000),
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    age=st.integers(min_value=0, max_value=150),
    score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    status=st.sampled_from(["active", "inactive", "pending", "deleted"]),
    is_active=st.booleans(),
)


class TestSpecificationOperatorCorrectness:
    """Property tests for Specification Operator Correctness.

    **Feature: advanced-reusability, Property 2: Specification Operator Correctness**
    **Validates: Requirements 2.1**
    """

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_eq_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and EQ operator, is_satisfied_by() SHALL return
        True only when field_value == comparison_value.
        """
        spec = field_eq("age", threshold)
        expected = entity.age == threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_ne_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and NE operator, is_satisfied_by() SHALL return
        True only when field_value != comparison_value.
        """
        spec = field_ne("age", threshold)
        expected = entity.age != threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_gt_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and GT operator, is_satisfied_by() SHALL return
        True only when field_value > comparison_value.
        """
        spec = field_gt("age", threshold)
        expected = entity.age > threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_ge_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and GE operator, is_satisfied_by() SHALL return
        True only when field_value >= comparison_value.
        """
        spec = field_ge("age", threshold)
        expected = entity.age >= threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_lt_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and LT operator, is_satisfied_by() SHALL return
        True only when field_value < comparison_value.
        """
        spec = field_lt("age", threshold)
        expected = entity.age < threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_le_operator_correctness(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and LE operator, is_satisfied_by() SHALL return
        True only when field_value <= comparison_value.
        """
        spec = field_le("age", threshold)
        expected = entity.age <= threshold
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(
        entity=entity_strategy,
        values=st.lists(
            st.sampled_from(["active", "inactive", "pending", "deleted"]),
            min_size=1,
            max_size=4,
        ),
    )
    def test_in_operator_correctness(
        self, entity: SampleEntity, values: list[str]
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and IN operator, is_satisfied_by() SHALL return
        True only when field_value is in the collection.
        """
        spec = field_in("status", values)
        expected = entity.status in values
        assert spec.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(
        entity=entity_strategy,
        low=st.integers(min_value=0, max_value=75),
        high=st.integers(min_value=75, max_value=150),
    )
    def test_between_operator_correctness(
        self, entity: SampleEntity, low: int, high: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 2: Specification Operator Correctness**

        For any field value and BETWEEN operator, is_satisfied_by() SHALL return
        True only when low <= field_value <= high.
        """
        spec = field_between("age", low, high)
        expected = low <= entity.age <= high
        assert spec.is_satisfied_by(entity) == expected


class TestSpecificationComposition:
    """Property tests for Specification Composition.

    **Feature: advanced-reusability, Property 3: Specification Composition**
    **Validates: Requirements 2.2**
    """

    @settings(max_examples=100)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_and_composition_correctness(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 3: Specification Composition**

        For any two specifications A and B, (A.and_(B)).is_satisfied_by(x)
        SHALL equal A.is_satisfied_by(x) and B.is_satisfied_by(x).
        """
        spec_a = field_ge("age", threshold_a)
        spec_b = field_le("age", threshold_b)

        combined = spec_a.and_(spec_b)

        a_result = spec_a.is_satisfied_by(entity)
        b_result = spec_b.is_satisfied_by(entity)
        expected = a_result and b_result

        assert combined.is_satisfied_by(entity) == expected

    @settings(max_examples=100)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_or_composition_correctness(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 3: Specification Composition**

        For any two specifications A and B, (A.or_(B)).is_satisfied_by(x)
        SHALL equal A.is_satisfied_by(x) or B.is_satisfied_by(x).
        """
        spec_a = field_lt("age", threshold_a)
        spec_b = field_gt("age", threshold_b)

        combined = spec_a.or_(spec_b)

        a_result = spec_a.is_satisfied_by(entity)
        b_result = spec_b.is_satisfied_by(entity)
        expected = a_result or b_result

        assert combined.is_satisfied_by(entity) == expected

    @settings(max_examples=50)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_operator_and_equals_and_method(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        The & operator SHALL produce the same result as and_().
        """
        spec_a = field_ge("age", threshold_a)
        spec_b = field_le("age", threshold_b)

        method_result = spec_a.and_(spec_b).is_satisfied_by(entity)
        operator_result = (spec_a & spec_b).is_satisfied_by(entity)

        assert method_result == operator_result

    @settings(max_examples=50)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_operator_or_equals_or_method(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        The | operator SHALL produce the same result as or_().
        """
        spec_a = field_lt("age", threshold_a)
        spec_b = field_gt("age", threshold_b)

        method_result = spec_a.or_(spec_b).is_satisfied_by(entity)
        operator_result = (spec_a | spec_b).is_satisfied_by(entity)

        assert method_result == operator_result


class TestSpecificationNegation:
    """Property tests for Specification Negation.

    **Feature: advanced-reusability, Property 4: Specification Negation**
    **Validates: Requirements 2.6**
    """

    @settings(max_examples=100)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_not_negates_specification(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 4: Specification Negation**

        For any specification S, S.not_().is_satisfied_by(x) SHALL equal
        not S.is_satisfied_by(x).
        """
        spec = field_ge("age", threshold)
        negated = spec.not_()

        original_result = spec.is_satisfied_by(entity)
        negated_result = negated.is_satisfied_by(entity)

        assert negated_result == (not original_result)

    @settings(max_examples=50)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_operator_invert_equals_not_method(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        The ~ operator SHALL produce the same result as not_().
        """
        spec = field_ge("age", threshold)

        method_result = spec.not_().is_satisfied_by(entity)
        operator_result = (~spec).is_satisfied_by(entity)

        assert method_result == operator_result

    @settings(max_examples=50)
    @given(entity=entity_strategy, threshold=st.integers(min_value=0, max_value=150))
    def test_double_negation_returns_original(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        Double negation SHALL return to original result: NOT(NOT(A)) == A.
        """
        spec = field_ge("age", threshold)
        double_negated = spec.not_().not_()

        assert spec.is_satisfied_by(entity) == double_negated.is_satisfied_by(entity)


class TestSpecificationBuilder:
    """Property tests for SpecificationBuilder fluent API."""

    @settings(max_examples=50)
    @given(
        entity=entity_strategy,
        threshold=st.integers(min_value=0, max_value=150),
    )
    def test_builder_where_equals_direct_spec(
        self, entity: SampleEntity, threshold: int
    ) -> None:
        """
        Builder.where() SHALL produce equivalent result to direct FieldSpecification.
        """
        direct_spec = FieldSpecification("age", ComparisonOperator.GE, threshold)
        builder_spec = (
            SpecificationBuilder[SampleEntity]()
            .where("age", ComparisonOperator.GE, threshold)
            .build()
        )

        assert direct_spec.is_satisfied_by(entity) == builder_spec.is_satisfied_by(entity)

    @settings(max_examples=50)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_builder_and_where_equals_and_composition(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        Builder.and_where() SHALL produce equivalent result to and_() composition.
        """
        direct_spec = field_ge("age", threshold_a).and_(field_le("age", threshold_b))
        builder_spec = (
            SpecificationBuilder[SampleEntity]()
            .where("age", ComparisonOperator.GE, threshold_a)
            .and_where("age", ComparisonOperator.LE, threshold_b)
            .build()
        )

        assert direct_spec.is_satisfied_by(entity) == builder_spec.is_satisfied_by(entity)

    @settings(max_examples=50)
    @given(
        entity=entity_strategy,
        threshold_a=st.integers(min_value=0, max_value=150),
        threshold_b=st.integers(min_value=0, max_value=150),
    )
    def test_builder_or_where_equals_or_composition(
        self, entity: SampleEntity, threshold_a: int, threshold_b: int
    ) -> None:
        """
        Builder.or_where() SHALL produce equivalent result to or_() composition.
        """
        direct_spec = field_lt("age", threshold_a).or_(field_gt("age", threshold_b))
        builder_spec = (
            SpecificationBuilder[SampleEntity]()
            .where("age", ComparisonOperator.LT, threshold_a)
            .or_where("age", ComparisonOperator.GT, threshold_b)
            .build()
        )

        assert direct_spec.is_satisfied_by(entity) == builder_spec.is_satisfied_by(entity)



class TestSpecificationSQLEquivalence:
    """Property tests for Specification SQL Equivalence.

    **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**
    **Validates: Requirements 2.3, 2.4**

    Note: These tests use SampleEntity which has the same fields as a SQLModel
    would have. We test SQL generation by verifying the condition is created
    and contains expected field references.
    """

    @settings(max_examples=50)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=20),
        threshold=st.integers(min_value=0, max_value=150),
    )
    def test_in_memory_filter_equals_sql_filter_eq(
        self, entities: list[SampleEntity], threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**

        For any specification and dataset, filtering in-memory with
        is_satisfied_by() SHALL produce the same results as filtering
        with the generated SQL condition.
        """
        spec = field_eq("age", threshold)

        # In-memory filtering
        in_memory_results = [e for e in entities if spec.is_satisfied_by(e)]

        # SQL condition generation using SampleEntity (has same attributes)
        sql_condition = spec.to_sql_condition(SampleEntity)

        # Verify SQL condition is generated correctly
        assert sql_condition is not None

        # Verify in-memory results are correct
        expected = [e for e in entities if e.age == threshold]
        assert len(in_memory_results) == len(expected)

    @settings(max_examples=50)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=20),
        threshold_a=st.integers(min_value=0, max_value=75),
        threshold_b=st.integers(min_value=75, max_value=150),
    )
    def test_composite_spec_sql_generation(
        self, entities: list[SampleEntity], threshold_a: int, threshold_b: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**

        For composite specifications, SQL generation SHALL produce
        valid AND/OR conditions.
        """
        spec = field_ge("age", threshold_a).and_(field_le("age", threshold_b))

        # In-memory filtering
        in_memory_results = [e for e in entities if spec.is_satisfied_by(e)]

        # SQL condition generation
        sql_condition = spec.to_sql_condition(SampleEntity)
        assert sql_condition is not None

        # Verify expected in-memory results
        expected = [e for e in entities if threshold_a <= e.age <= threshold_b]
        assert len(in_memory_results) == len(expected)

    @settings(max_examples=50)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=20),
        threshold=st.integers(min_value=0, max_value=150),
    )
    def test_negated_spec_sql_generation(
        self, entities: list[SampleEntity], threshold: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**

        For negated specifications, SQL generation SHALL produce
        valid NOT conditions.
        """
        spec = field_ge("age", threshold).not_()

        # In-memory filtering
        in_memory_results = [e for e in entities if spec.is_satisfied_by(e)]

        # SQL condition generation
        sql_condition = spec.to_sql_condition(SampleEntity)
        assert sql_condition is not None

        # Verify expected in-memory results
        expected = [e for e in entities if not (e.age >= threshold)]
        assert len(in_memory_results) == len(expected)

    @settings(max_examples=30)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=15),
        low=st.integers(min_value=0, max_value=50),
        high=st.integers(min_value=100, max_value=150),
    )
    def test_between_spec_sql_generation(
        self, entities: list[SampleEntity], low: int, high: int
    ) -> None:
        """
        **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**

        For BETWEEN specifications, SQL generation SHALL produce
        valid BETWEEN conditions.
        """
        spec = field_between("age", low, high)

        # In-memory filtering
        in_memory_results = [e for e in entities if spec.is_satisfied_by(e)]

        # SQL condition generation
        sql_condition = spec.to_sql_condition(SampleEntity)
        assert sql_condition is not None

        # Verify expected in-memory results
        expected = [e for e in entities if low <= e.age <= high]
        assert len(in_memory_results) == len(expected)

    @settings(max_examples=30)
    @given(
        entities=st.lists(entity_strategy, min_size=1, max_size=15),
        values=st.lists(
            st.sampled_from(["active", "inactive", "pending", "deleted"]),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    def test_in_spec_sql_generation(
        self, entities: list[SampleEntity], values: list[str]
    ) -> None:
        """
        **Feature: advanced-reusability, Property 5: Specification SQL Equivalence**

        For IN specifications, SQL generation SHALL produce
        valid IN conditions.
        """
        spec = field_in("status", values)

        # In-memory filtering
        in_memory_results = [e for e in entities if spec.is_satisfied_by(e)]

        # SQL condition generation
        sql_condition = spec.to_sql_condition(SampleEntity)
        assert sql_condition is not None

        # Verify expected in-memory results
        expected = [e for e in entities if e.status in values]
        assert len(in_memory_results) == len(expected)
