# Service vs UseCase - Guia de Arquitetura

## Resumo

| Padrão | Responsabilidade | Métodos | Quando Usar |
|--------|------------------|---------|-------------|
| **Service** | CRUD + operações de uma entidade | `create()`, `update()`, `delete()`, `get()`, `list()` | Operações simples em uma entidade |
| **UseCase** | Operação de negócio complexa | `execute()` | Orquestração de múltiplos serviços |

## Service (GenericService)

Use `GenericService` para operações CRUD em uma única entidade:

```python
from application.common.services import GenericService

class ItemService(GenericService[Item, CreateDTO, UpdateDTO, ResponseDTO]):
    entity_name = "Item"
    
    async def _pre_create(self, data: CreateDTO) -> Result[CreateDTO, ServiceError]:
        # Validação customizada
        if data.price <= 0:
            return Err(ValidationError("Price must be positive", "price"))
        return Ok(data)
```

### Características:
- Múltiplos métodos CRUD
- Hooks de validação (`_pre_create`, `_post_update`, etc.)
- Integração com `GenericCRUDRouter`
- Result pattern para erros

## UseCase (BaseUseCase)

Use `BaseUseCase` para operações de negócio complexas:

```python
from application.common.use_cases import BaseUseCase, UseCaseResult

class PlaceOrderUseCase(BaseUseCase[PlaceOrderInput, PlaceOrderOutput]):
    def __init__(self, inventory, payment, orders, notifications):
        super().__init__()
        self._inventory = inventory
        self._payment = payment
        self._orders = orders
        self._notifications = notifications
    
    async def execute(self, input: PlaceOrderInput) -> UseCaseResult[PlaceOrderOutput]:
        # 1. Validar input
        # 2. Verificar estoque
        # 3. Processar pagamento
        # 4. Criar pedido
        # 5. Enviar notificação
        ...
```

### Características:
- Único método `execute()`
- Orquestra múltiplos serviços
- Transações compensatórias (rollback)
- Regras de negócio complexas

## Exemplos no Projeto

### Service
- `src/application/examples/item/services/item_service.py` - CRUD de itens

### UseCase
- `src/application/examples/order/use_cases/place_order.py` - Realizar pedido

## Fluxo de Decisão

```
Preciso fazer CRUD simples em uma entidade?
├── SIM → Use GenericService
└── NÃO → A operação envolve múltiplos serviços/entidades?
          ├── SIM → Use BaseUseCase
          └── NÃO → Use GenericService com hooks customizados
```

## Localização dos Arquivos

```
src/application/
├── common/
│   ├── services/
│   │   ├── generic_service.py    # Base para Services
│   │   └── __init__.py
│   └── use_cases/
│       ├── base_use_case.py      # Base para UseCases
│       └── __init__.py
└── examples/
    ├── item/
    │   └── services/
    │       └── item_service.py   # Exemplo de Service
    └── order/
        └── use_cases/
            └── place_order.py    # Exemplo de UseCase
```
