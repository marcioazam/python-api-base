# Bounded Context Template

## Directory Structure

```
src/
├── domain/[context]/
│   ├── __init__.py
│   ├── entities.py
│   ├── repository.py
│   ├── value_objects.py
│   ├── events.py
│   └── specifications.py
├── application/[context]/
│   ├── __init__.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── create_[entity].py
│   │   ├── update_[entity].py
│   │   └── delete_[entity].py
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── get_[entity].py
│   │   └── list_[entities].py
│   ├── dtos.py
│   └── mappers.py
└── interface/v1/
    └── [context].py
```

## Entity Template

```python
# src/domain/[context]/entities.py
from dataclasses import dataclass, field
from datetime import datetime
from ulid import ULID

@dataclass
class [Entity]:
    """[Entity] domain entity."""
    
    id: str = field(default_factory=lambda: str(ULID()))
    # Add entity fields
    name: str
    # ...
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    # Domain methods
    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
```

## Repository Interface Template

```python
# src/domain/[context]/repository.py
from typing import Protocol
from .entities import [Entity]

class I[Entity]Repository(Protocol):
    """Repository interface for [Entity]."""
    
    async def get(self, id: str) -> [Entity] | None: ...
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[[Entity]]: ...
    async def create(self, entity: [Entity]) -> [Entity]: ...
    async def update(self, entity: [Entity]) -> [Entity]: ...
    async def delete(self, id: str) -> bool: ...
    async def exists(self, id: str) -> bool: ...
    
    # Add domain-specific methods
    # async def find_by_[field](self, [field]: str) -> [Entity] | None: ...
```

## DTO Template

```python
# src/application/[context]/dtos.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class [Entity]DTO(BaseModel):
    """[Entity] data transfer object."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    created_at: datetime
    updated_at: datetime | None = None

class Create[Entity]DTO(BaseModel):
    """DTO for creating [Entity]."""
    
    name: str = Field(min_length=1, max_length=100)

class Update[Entity]DTO(BaseModel):
    """DTO for updating [Entity]."""
    
    name: str | None = Field(None, min_length=1, max_length=100)
```

## Command Template

```python
# src/application/[context]/commands/create_[entity].py
from dataclasses import dataclass
from result import Result, Ok, Err
from domain.[context].entities import [Entity]
from domain.[context].repository import I[Entity]Repository

@dataclass
class Create[Entity]Command:
    """Command to create a new [Entity]."""
    
    name: str
    
    async def execute(
        self,
        repository: I[Entity]Repository,
    ) -> Result[[Entity], str]:
        # Validation
        # ...
        
        # Create entity
        entity = [Entity](name=self.name)
        
        # Persist
        created = await repository.create(entity)
        return Ok(created)
```

## Router Template

```python
# src/interface/v1/[context].py
from fastapi import APIRouter, Depends, HTTPException
from application.[context].dtos import [Entity]DTO, Create[Entity]DTO
from application.[context].commands import Create[Entity]Command

router = APIRouter(prefix="/[entities]", tags=["[Entities]"])

@router.post("/", response_model=[Entity]DTO, status_code=201)
async def create_[entity](
    data: Create[Entity]DTO,
    command_bus = Depends(get_command_bus),
) -> [Entity]DTO:
    command = Create[Entity]Command(**data.model_dump())
    result = await command_bus.dispatch(command)
    
    if result.is_err():
        raise HTTPException(400, detail=result.error)
    
    return [Entity]DTO.model_validate(result.value)

@router.get("/{id}", response_model=[Entity]DTO)
async def get_[entity](
    id: str,
    query_bus = Depends(get_query_bus),
) -> [Entity]DTO:
    result = await query_bus.dispatch(Get[Entity]Query(id=id))
    
    if result is None:
        raise HTTPException(404, detail="[Entity] not found")
    
    return result
```

## Migration Template

```python
# alembic/versions/xxx_add_[entities]_table.py
def upgrade():
    op.create_table(
        '[entities]',
        sa.Column('id', sa.String(26), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )

def downgrade():
    op.drop_table('[entities]')
```
