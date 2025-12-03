"""Property-based tests for Infrastructure Modules Audit.

**Feature: infrastructure-modules-audit**

This module contains property-based tests for:
- Module import verification
- Active modules reachability from main
- Error hierarchy consistency
"""

import pytest
from hypothesis import given, settings, strategies as st


# =============================================================================
# Property 1: All Infrastructure Modules Import Successfully
# **Feature: infrastructure-modules-audit, Property 1**
# **Validates: Requirements 5.1, 5.3**
# =============================================================================

class TestInfrastructureModulesImport:
    """Property tests for infrastructure module imports.
    
    *For any* infrastructure module in the analyzed set, importing the module
    SHALL NOT raise ImportError or ModuleNotFoundError.
    """

    def test_errors_module_imports(self) -> None:
        """infrastructure.errors imports successfully."""
        from infrastructure.errors import (
            InfrastructureError,
            DatabaseError,
            ConnectionPoolError,
            ExternalServiceError,
            CacheError,
            MessagingError,
            StorageError,
            TokenStoreError,
            TokenValidationError,
            AuditLogError,
            TelemetryError,
            ConfigurationError,
        )
        assert InfrastructureError is not None
        assert DatabaseError is not None

    def test_httpclient_module_imports(self) -> None:
        """infrastructure.httpclient imports successfully."""
        from infrastructure.httpclient import (
            HttpClient,
            HttpClientConfig,
            HttpError,
            TimeoutError,
            ValidationError,
            RetryPolicy,
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
        )
        assert HttpClient is not None
        assert RetryPolicy is not None
        assert CircuitBreaker is not None

    def test_feature_flags_module_imports(self) -> None:
        """infrastructure.feature_flags imports successfully."""
        from infrastructure.feature_flags import (
            EvaluationContext,
            EvaluationResult,
            FeatureFlag,
            FeatureFlagEvaluator,
            FeatureFlagStore,
            FlagAuditLogger,
            FlagEvaluationLog,
            FlagStatus,
            InMemoryFeatureFlagStore,
        )
        assert FeatureFlag is not None
        assert FeatureFlagEvaluator is not None

    def test_generics_module_imports(self) -> None:
        """infrastructure.generics imports successfully."""
        from infrastructure.generics import (
            Repository,
            Service,
            Factory,
            Store,
            AsyncRepository,
            AsyncService,
            ErrorMessages,
            InfrastructureError,
            ValidationError,
            BaseStatus,
            ConnectionStatus,
            TaskStatus,
            HealthStatus,
            CacheStatus,
            validate_non_empty,
            validate_range,
            validate_format,
            validate_required,
            ValidationResult,
            BaseConfig,
            ConfigBuilder,
        )
        assert Repository is not None
        assert ErrorMessages is not None

    def test_elasticsearch_module_imports(self) -> None:
        """infrastructure.elasticsearch imports successfully."""
        from infrastructure.elasticsearch import (
            ElasticsearchClient,
            ElasticsearchClientConfig,
            ElasticsearchRepository,
            SearchQuery,
            SearchResult,
            AggregationResult,
            ElasticsearchDocument,
            DocumentMetadata,
        )
        assert ElasticsearchClient is not None
        assert ElasticsearchDocument is not None


# =============================================================================
# Property 2: Active Modules Are Reachable from Main
# **Feature: infrastructure-modules-audit, Property 2**
# **Validates: Requirements 2.3**
# =============================================================================

class TestActiveModulesReachability:
    """Property tests for active modules reachability.
    
    *For any* module marked as "active", there SHALL exist an import path
    from main.py to that module.
    """

    def test_errors_reachable_from_main(self) -> None:
        """infrastructure.errors is reachable from main via db.session."""
        import inspect
        from infrastructure.db import session
        source = inspect.getsource(session)
        assert "from infrastructure.errors" in source

    def test_feature_flags_reachable_from_middleware(self) -> None:
        """infrastructure.feature_flags is reachable from middleware."""
        import inspect
        from interface.middleware import production
        source = inspect.getsource(production)
        assert "from infrastructure.feature_flags" in source

    def test_main_imports_middleware(self) -> None:
        """main.py imports production middleware."""
        import inspect
        import main
        source = inspect.getsource(main)
        assert "setup_production_middleware" in source


# =============================================================================
# Property 5: Error Hierarchy Consistency
# **Feature: infrastructure-modules-audit, Property 5**
# **Validates: Requirements 1.1**
# =============================================================================

class TestErrorHierarchyConsistency:
    """Property tests for error hierarchy consistency.
    
    *For any* error class in infrastructure.errors, it SHALL inherit from
    InfrastructureError and be catchable by catching InfrastructureError.
    """

    def test_all_errors_inherit_from_infrastructure_error(self) -> None:
        """All error classes inherit from InfrastructureError."""
        from infrastructure.errors import (
            InfrastructureError,
            DatabaseError,
            ConnectionPoolError,
            ExternalServiceError,
            CacheError,
            MessagingError,
            StorageError,
            TokenStoreError,
            TokenValidationError,
            AuditLogError,
            TelemetryError,
            ConfigurationError,
        )
        
        error_classes = [
            DatabaseError,
            ConnectionPoolError,
            ExternalServiceError,
            CacheError,
            MessagingError,
            StorageError,
            TokenStoreError,
            TokenValidationError,
            AuditLogError,
            TelemetryError,
            ConfigurationError,
        ]
        
        for error_class in error_classes:
            assert issubclass(error_class, InfrastructureError), \
                f"{error_class.__name__} should inherit from InfrastructureError"

    def test_errors_catchable_by_base(self) -> None:
        """All errors are catchable by catching InfrastructureError."""
        from infrastructure.errors import (
            InfrastructureError,
            DatabaseError,
            CacheError,
            TokenStoreError,
        )
        
        # Test DatabaseError
        try:
            raise DatabaseError("test")
        except InfrastructureError:
            pass  # Expected
        
        # Test CacheError
        try:
            raise CacheError("test")
        except InfrastructureError:
            pass  # Expected
        
        # Test TokenStoreError
        try:
            raise TokenStoreError("test")
        except InfrastructureError:
            pass  # Expected

    @given(message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_error_message_preserved(self, message: str) -> None:
        """Error message is preserved in all error types."""
        from infrastructure.errors import (
            InfrastructureError,
            DatabaseError,
            CacheError,
        )
        
        # InfrastructureError
        error = InfrastructureError(message)
        assert error.message == message
        
        # DatabaseError
        error = DatabaseError(message)
        assert error.message == message
        
        # CacheError
        error = CacheError(message)
        assert error.message == message
