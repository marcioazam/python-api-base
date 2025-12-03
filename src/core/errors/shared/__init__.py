"""Shared module exceptions.

**Feature: shared-modules-refactoring**
"""

from core.errors.shared.exceptions import (
    AuthenticationError,
    BanOperationError,
    DecryptionError,
    EncryptionError,
    EntityResolutionError,
    FederationValidationError,
    FilterValidationError,
    LockAcquisitionTimeout,
    PatternValidationError,
    Phase2ModuleError,
    PoolInvariantViolation,
    RollbackError,
    SecurityModuleError,
    SharedModuleError,
    SnapshotIntegrityError,
    TaskExecutionError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "BanOperationError",
    "DecryptionError",
    "EncryptionError",
    "EntityResolutionError",
    "FederationValidationError",
    "FilterValidationError",
    "LockAcquisitionTimeout",
    "PatternValidationError",
    "Phase2ModuleError",
    "PoolInvariantViolation",
    "RollbackError",
    "SecurityModuleError",
    "SharedModuleError",
    "SnapshotIntegrityError",
    "TaskExecutionError",
    "ValidationError",
]
