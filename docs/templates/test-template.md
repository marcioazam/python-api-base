# Test Templates

## Unit Test Template

```python
# tests/unit/domain/[module]/test_[component].py
import pytest
from domain.[module].[component] import [Class]

class Test[Class]:
    """Tests for [Class]."""
    
    def test_[method]_with_valid_input(self):
        """[Method] should [expected behavior] when [condition]."""
        # Arrange
        instance = [Class](...)
        
        # Act
        result = instance.[method](...)
        
        # Assert
        assert result == expected
    
    def test_[method]_with_invalid_input_raises(self):
        """[Method] should raise [Error] when [condition]."""
        # Arrange
        instance = [Class](...)
        
        # Act & Assert
        with pytest.raises([Error]):
            instance.[method](invalid_input)
```

## Async Test Template

```python
# tests/unit/application/[module]/test_[use_case].py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_[use_case]_success():
    """[UseCase] should [expected behavior] when [condition]."""
    # Arrange
    repository = AsyncMock()
    repository.get.return_value = [expected_entity]
    
    use_case = [UseCase](repository=repository)
    
    # Act
    result = await use_case.execute(...)
    
    # Assert
    assert result.is_ok()
    repository.get.assert_called_once_with(...)
```

## Property Test Template

```python
# tests/properties/test_[component]_properties.py
from hypothesis import given, strategies as st

class Test[Component]Properties:
    """Property-based tests for [Component]."""
    
    @given(st.[strategy]())
    def test_[property_name](self, value):
        """
        **Feature: [feature_name], Property [N]: [Property Name]**
        **Validates: Requirements [X.Y]**
        
        [Property description]
        """
        # Arrange
        instance = [Class](value)
        
        # Act
        result = instance.[method]()
        
        # Assert
        assert [property_holds]
```

## Integration Test Template

```python
# tests/integration/[module]/test_[component].py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_[endpoint]_success(client: AsyncClient):
    """[Endpoint] should return [expected] when [condition]."""
    # Arrange
    payload = {...}
    
    # Act
    response = await client.post("/api/v1/[endpoint]", json=payload)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == expected
```

## E2E Test Template

```python
# tests/e2e/test_[flow].py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_[flow]_lifecycle(client: AsyncClient):
    """Test complete [flow] lifecycle."""
    
    # 1. Create
    create_response = await client.post("/api/v1/[resource]", json={...})
    assert create_response.status_code == 201
    resource_id = create_response.json()["id"]
    
    # 2. Read
    get_response = await client.get(f"/api/v1/[resource]/{resource_id}")
    assert get_response.status_code == 200
    
    # 3. Update
    update_response = await client.patch(f"/api/v1/[resource]/{resource_id}", json={...})
    assert update_response.status_code == 200
    
    # 4. Delete
    delete_response = await client.delete(f"/api/v1/[resource]/{resource_id}")
    assert delete_response.status_code == 204
    
    # 5. Verify deleted
    verify_response = await client.get(f"/api/v1/[resource]/{resource_id}")
    assert verify_response.status_code == 404
```

## Fixture Template

```python
# tests/conftest.py
import pytest

@pytest.fixture
def sample_[entity]():
    """Create a sample [entity] for testing."""
    return [Entity](
        id="test-123",
        field="value",
    )

@pytest.fixture
async def created_[entity](db_session):
    """Create and persist a [entity]."""
    repository = [Repository](db_session)
    entity = [Entity](...)
    return await repository.create(entity)
```
