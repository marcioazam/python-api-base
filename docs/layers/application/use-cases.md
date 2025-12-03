# Use Cases

## Overview

Use Cases orquestram operações de negócio, coordenando entre entidades de domínio, repositórios e serviços externos.

## Use Case Structure

```python
from dataclasses import dataclass
from result import Result, Ok, Err

@dataclass
class CreateUserUseCase:
    """Use case for creating a new user."""
    
    repository: IUserRepository
    password_hasher: PasswordHasher
    event_publisher: EventPublisher
    
    async def execute(self, data: CreateUserDTO) -> Result[UserDTO, str]:
        # 1. Validate business rules
        if await self.repository.exists_by_email(data.email):
            return Err("Email already exists")
        
        # 2. Create domain entity
        user = User.create(
            email=data.email,
            name=data.name,
            password_hash=self.password_hasher.hash(data.password),
        )
        
        # 3. Persist
        created = await self.repository.create(user)
        
        # 4. Publish events
        await self.event_publisher.publish(UserCreated(
            user_id=created.id,
            email=created.email,
        ))
        
        # 5. Return DTO
        return Ok(UserMapper.to_dto(created))
```

## Use Case with Transaction

```python
@dataclass
class TransferMoneyUseCase:
    """Use case for transferring money between accounts."""
    
    account_repository: IAccountRepository
    transaction_repository: ITransactionRepository
    unit_of_work: UnitOfWork
    
    async def execute(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: Decimal,
    ) -> Result[TransactionDTO, str]:
        async with self.unit_of_work:
            # Get accounts
            from_account = await self.account_repository.get(from_account_id)
            to_account = await self.account_repository.get(to_account_id)
            
            if not from_account or not to_account:
                return Err("Account not found")
            
            # Business logic
            if from_account.balance < amount:
                return Err("Insufficient funds")
            
            # Update accounts
            from_account.withdraw(amount)
            to_account.deposit(amount)
            
            await self.account_repository.update(from_account)
            await self.account_repository.update(to_account)
            
            # Create transaction record
            transaction = Transaction.create(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
            )
            await self.transaction_repository.create(transaction)
            
            # Commit happens automatically on context exit
            return Ok(TransactionMapper.to_dto(transaction))
```

## Use Case with Specification

```python
@dataclass
class SearchUsersUseCase:
    """Use case for searching users with filters."""
    
    repository: IUserRepository
    
    async def execute(
        self,
        filters: UserSearchFilters,
    ) -> UserListDTO:
        # Build specification from filters
        spec = self._build_specification(filters)
        
        # Query with specification
        users = await self.repository.find_by_spec(
            spec=spec,
            skip=filters.skip,
            limit=filters.limit,
        )
        total = await self.repository.count_by_spec(spec)
        
        return UserListDTO(
            items=UserMapper.to_dto_list(users),
            total=total,
            skip=filters.skip,
            limit=filters.limit,
        )
    
    def _build_specification(self, filters: UserSearchFilters) -> Specification[User]:
        specs = []
        
        if filters.is_active is not None:
            specs.append(equals("is_active", filters.is_active))
        
        if filters.search:
            specs.append(
                contains("name", filters.search).or_spec(
                    contains("email", filters.search)
                )
            )
        
        if filters.created_after:
            specs.append(greater_than("created_at", filters.created_after))
        
        # Combine all specs with AND
        if not specs:
            return TrueSpecification()
        
        result = specs[0]
        for spec in specs[1:]:
            result = result.and_spec(spec)
        
        return result
```

## Use Case with External Service

```python
@dataclass
class ProcessPaymentUseCase:
    """Use case for processing a payment."""
    
    order_repository: IOrderRepository
    payment_gateway: PaymentGateway
    notification_service: NotificationService
    
    async def execute(
        self,
        order_id: str,
        payment_method: PaymentMethod,
    ) -> Result[PaymentDTO, str]:
        # Get order
        order = await self.order_repository.get(order_id)
        if not order:
            return Err("Order not found")
        
        if order.status != OrderStatus.PENDING:
            return Err("Order is not pending")
        
        # Process payment (external service)
        payment_result = await self.payment_gateway.charge(
            amount=order.total,
            method=payment_method,
            reference=order.id,
        )
        
        if payment_result.is_err():
            return Err(f"Payment failed: {payment_result.error}")
        
        # Update order
        order.mark_paid(payment_result.value.transaction_id)
        await self.order_repository.update(order)
        
        # Send notification (fire and forget)
        await self.notification_service.send_payment_confirmation(
            order_id=order.id,
            amount=order.total,
        )
        
        return Ok(PaymentMapper.to_dto(payment_result.value))
```

## Testing Use Cases

```python
@pytest.mark.asyncio
async def test_create_user_success():
    # Arrange
    repository = AsyncMock(spec=IUserRepository)
    repository.exists_by_email.return_value = False
    repository.create.return_value = User(id="123", email="test@example.com", name="Test")
    
    hasher = Mock(spec=PasswordHasher)
    hasher.hash.return_value = "hashed"
    
    publisher = AsyncMock(spec=EventPublisher)
    
    use_case = CreateUserUseCase(
        repository=repository,
        password_hasher=hasher,
        event_publisher=publisher,
    )
    
    # Act
    result = await use_case.execute(CreateUserDTO(
        email="test@example.com",
        name="Test",
        password="password123",
    ))
    
    # Assert
    assert result.is_ok()
    assert result.value.email == "test@example.com"
    repository.create.assert_called_once()
    publisher.publish.assert_called_once()
```

## Best Practices

1. **Single responsibility** - One use case per operation
2. **Return Result type** - For explicit error handling
3. **Use DTOs** - Don't expose entities
4. **Inject dependencies** - For testability
5. **Keep thin** - Delegate to domain
