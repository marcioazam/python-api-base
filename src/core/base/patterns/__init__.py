"""Design patterns base classes.

**Feature: architecture-restructuring-2025**
"""

from core.base.patterns.pagination import CursorPage, CursorPagination
from core.base.patterns.result import (
    Err,
    Ok,
    Result,
    collect_results,
    err,
    ok,
    result_from_dict,
    try_catch,
    try_catch_async,
)
from core.base.patterns.specification import (
    AndSpecification,
    AttributeSpecification,
    CompositeSpecification,
    FalseSpecification,
    NotSpecification,
    OrSpecification,
    PredicateSpecification,
    Specification,
    TrueSpecification,
)
from core.base.patterns.uow import UnitOfWork
from core.base.patterns.use_case import BaseUseCase, IMapper, IRepository
from core.base.patterns.validation import (
    AlternativeValidator,
    ChainedValidator,
    CompositeValidator,
    FieldError,
    NotEmptyValidator,
    PredicateValidator,
    RangeValidator,
    ValidationError,
    Validator,
    validate_all,
)

__all__ = [
    # Result
    "Ok",
    "Err",
    "Result",
    "ok",
    "err",
    "try_catch",
    "try_catch_async",
    "collect_results",
    "result_from_dict",
    # Pagination
    "CursorPage",
    "CursorPagination",
    # Specification
    "Specification",
    "CompositeSpecification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    "TrueSpecification",
    "FalseSpecification",
    "PredicateSpecification",
    "AttributeSpecification",
    # UoW
    "UnitOfWork",
    # UseCase
    "BaseUseCase",
    "IMapper",
    "IRepository",
    # Validation
    "FieldError",
    "ValidationError",
    "Validator",
    "CompositeValidator",
    "ChainedValidator",
    "AlternativeValidator",
    "PredicateValidator",
    "NotEmptyValidator",
    "RangeValidator",
    "validate_all",
]
