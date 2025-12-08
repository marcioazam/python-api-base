"""Tests for validation middleware module.

Tests for ValidationMiddleware class.
"""

from dataclasses import dataclass
from typing import Any

import pytest

from application.common.errors import ValidationError
from application.common.middleware.validation.base import Validator
from application.common.middleware.validation.middleware import ValidationMiddleware
from core.base.patterns.result import Err, Ok, Result


@dataclass
class CreateUserCommand:
    """Sample command for testing."""

    email: str
    password: str


@dataclass
class DeleteUserCommand:
    """Another sample command for testing."""

    user_id: str


class EmailValidator(Validator[CreateUserCommand]):
    """Validator that checks email format."""

    def validate(self, command: CreateUserCommand) -> list[dict[str, Any]]:
        errors = []
        if not command.email:
            errors.append({"field": "email", "message": "Email is required"})
        elif "@" not in command.email:
            errors.append({"field": "email", "message": "Invalid email format"})
        return errors


class PasswordValidator(Validator[CreateUserCommand]):
    """Validator that checks password strength."""

    def validate(self, command: CreateUserCommand) -> list[dict[str, Any]]:
        errors = []
        if not command.password:
            errors.append({"field": "password", "message": "Password is required"})
        elif len(command.password) < 8:
            errors.append(
                {"field": "password", "message": "Password must be at least 8 characters"}
            )
        return errors


class AlwaysFailValidator(Validator[Any]):
    """Validator that always fails."""

    def validate(self, command: Any) -> list[dict[str, Any]]:
        return [{"field": "test", "message": "Always fails"}]


class AlwaysPassValidator(Validator[Any]):
    """Validator that always passes."""

    def validate(self, command: Any) -> list[dict[str, Any]]:
        return []


class TestValidationMiddleware:
    """Tests for ValidationMiddleware class."""

    def test_init_stores_validators(self) -> None:
        """Middleware should store validators mapping."""
        validators = {CreateUserCommand: [EmailValidator()]}
        middleware = ValidationMiddleware(validators)
        assert middleware._validators is validators

    def test_init_default_fail_fast(self) -> None:
        """Middleware should default to fail_fast=False."""
        middleware = ValidationMiddleware({})
        assert middleware._fail_fast is False

    def test_init_custom_fail_fast(self) -> None:
        """Middleware should accept fail_fast parameter."""
        middleware = ValidationMiddleware({}, fail_fast=True)
        assert middleware._fail_fast is True

    @pytest.mark.asyncio
    async def test_call_no_validators(self) -> None:
        """Middleware should pass through if no validators registered."""
        middleware = ValidationMiddleware({})
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("success")

        result = await middleware(command, handler)
        assert result.is_ok()
        assert result.unwrap() == "success"

    @pytest.mark.asyncio
    async def test_call_validation_passes(self) -> None:
        """Middleware should call handler if validation passes."""
        validators = {CreateUserCommand: [EmailValidator(), PasswordValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("user created")

        result = await middleware(command, handler)
        assert result.is_ok()
        assert result.unwrap() == "user created"

    @pytest.mark.asyncio
    async def test_call_validation_fails(self) -> None:
        """Middleware should return Err if validation fails."""
        validators = {CreateUserCommand: [EmailValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="invalid", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("should not reach")

        result = await middleware(command, handler)
        assert result.is_err()
        error = result.error
        assert isinstance(error, ValidationError)

    @pytest.mark.asyncio
    async def test_call_collects_all_errors(self) -> None:
        """Middleware should collect errors from all validators."""
        validators = {CreateUserCommand: [EmailValidator(), PasswordValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="", password="")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("should not reach")

        result = await middleware(command, handler)
        assert result.is_err()
        error = result.error
        assert isinstance(error, ValidationError)
        # Should have errors from both validators
        assert len(error.errors) >= 2

    @pytest.mark.asyncio
    async def test_call_fail_fast_stops_early(self) -> None:
        """Middleware with fail_fast should stop on first error."""
        validators = {CreateUserCommand: [AlwaysFailValidator(), AlwaysFailValidator()]}
        middleware = ValidationMiddleware(validators, fail_fast=True)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("should not reach")

        result = await middleware(command, handler)
        assert result.is_err()
        error = result.error
        assert isinstance(error, ValidationError)
        # Should only have one error due to fail_fast
        assert len(error.errors) == 1

    @pytest.mark.asyncio
    async def test_call_unregistered_command_type(self) -> None:
        """Middleware should pass through unregistered command types."""
        validators = {CreateUserCommand: [EmailValidator()]}
        middleware = ValidationMiddleware(validators)
        command = DeleteUserCommand(user_id="123")

        async def handler(cmd: DeleteUserCommand) -> Result[str, Exception]:
            return Ok("deleted")

        result = await middleware(command, handler)
        assert result.is_ok()
        assert result.unwrap() == "deleted"

    @pytest.mark.asyncio
    async def test_call_empty_validators_list(self) -> None:
        """Middleware should pass through if validators list is empty."""
        validators: dict[type, list[Validator[Any]]] = {CreateUserCommand: []}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("success")

        result = await middleware(command, handler)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_call_all_validators_pass(self) -> None:
        """Middleware should pass if all validators pass."""
        validators = {CreateUserCommand: [AlwaysPassValidator(), AlwaysPassValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("success")

        result = await middleware(command, handler)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_call_error_message_includes_command_name(self) -> None:
        """Validation error message should include command type name."""
        validators = {CreateUserCommand: [AlwaysFailValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Ok("should not reach")

        result = await middleware(command, handler)
        assert result.is_err()
        error = result.error
        assert isinstance(error, ValidationError)
        assert "CreateUserCommand" in str(error)

    @pytest.mark.asyncio
    async def test_call_preserves_handler_result(self) -> None:
        """Middleware should preserve complex handler results."""
        validators = {CreateUserCommand: [AlwaysPassValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[dict, Exception]:
            return Ok({"id": "123", "email": cmd.email, "status": "active"})

        result = await middleware(command, handler)
        assert result.is_ok()
        data = result.unwrap()
        assert data["id"] == "123"
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_call_handler_error_propagates(self) -> None:
        """Middleware should propagate handler errors."""
        validators = {CreateUserCommand: [AlwaysPassValidator()]}
        middleware = ValidationMiddleware(validators)
        command = CreateUserCommand(email="test@example.com", password="password123")

        async def handler(cmd: CreateUserCommand) -> Result[str, Exception]:
            return Err(RuntimeError("handler error"))

        result = await middleware(command, handler)
        assert result.is_err()
        assert isinstance(result.error, RuntimeError)
