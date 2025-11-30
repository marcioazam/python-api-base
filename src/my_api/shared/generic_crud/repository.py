"""Generic Repository Pattern with type safety and async support."""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel


class FilterOperator(Enum):
    """Filter operators for queries."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


@dataclass
class FilterCondition:
    """Single filter condition."""

    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = True


@dataclass
class SortCondition:
    """Sort condition."""

    field: str
    ascending: bool = True


@dataclass
class QueryOptions:
    """Query options for repository operations."""

    filters: list[FilterCondition] = field(default_factory=list)
    sorts: list[SortCondition] = field(default_factory=list)
    limit: int | None = None
    offset: int | None = None
    include_relations: list[str] = field(default_factory=list)
    select_fields: list[str] | None = None


@dataclass
class PaginatedResult[T]:
    """Paginated query result."""

    items: list[T]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class GenericRepository[T: SQLModel](ABC):
    """Generic repository base class with type safety."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def model(self) -> type[T]:
        return self._model

    def _build_query(self, options: QueryOptions) -> Any:
        """Build SQLAlchemy query from options."""
        query = select(self._model)

        if options.filters:
            conditions = []
            for filter_cond in options.filters:
                condition = self._build_filter_condition(filter_cond)
                if condition is not None:
                    conditions.append(condition)
            if conditions:
                query = query.where(and_(*conditions))

        if options.sorts:
            for sort_cond in options.sorts:
                field_attr = getattr(self._model, sort_cond.field, None)
                if field_attr is not None:
                    query = query.order_by(field_attr.asc() if sort_cond.ascending else field_attr.desc())

        if options.include_relations:
            for relation in options.include_relations:
                if hasattr(self._model, relation):
                    query = query.options(selectinload(getattr(self._model, relation)))

        if options.select_fields:
            fields = [getattr(self._model, f) for f in options.select_fields if hasattr(self._model, f)]
            if fields:
                query = select(*fields)

        return query

    def _build_filter_condition(self, filter_cond: FilterCondition) -> Any:
        """Build SQLAlchemy filter condition."""
        field_attr = getattr(self._model, filter_cond.field, None)
        if field_attr is None:
            return None

        op = filter_cond.operator
        value = filter_cond.value

        match op:
            case FilterOperator.EQ:
                return field_attr == value
            case FilterOperator.NE:
                return field_attr != value
            case FilterOperator.GT:
                return field_attr > value
            case FilterOperator.GTE:
                return field_attr >= value
            case FilterOperator.LT:
                return field_attr < value
            case FilterOperator.LTE:
                return field_attr <= value
            case FilterOperator.IN:
                return field_attr.in_(value)
            case FilterOperator.NOT_IN:
                return ~field_attr.in_(value)
            case FilterOperator.LIKE:
                return field_attr.like(value) if filter_cond.case_sensitive else field_attr.ilike(value)
            case FilterOperator.ILIKE:
                return field_attr.ilike(value)
            case FilterOperator.IS_NULL:
                return field_attr.is_(None)
            case FilterOperator.IS_NOT_NULL:
                return field_attr.is_not(None)
            case FilterOperator.BETWEEN:
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    return field_attr.between(value[0], value[1])
        return None

    async def create[CreateSchemaType](self, obj_in: CreateSchemaType) -> T:
        """Create a new record."""
        data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        db_obj = self._model(**data)
        self._session.add(db_obj)
        await self._session.commit()
        await self._session.refresh(db_obj)
        return db_obj

    async def get(self, id: Any, options: QueryOptions | None = None) -> T | None:
        """Get a record by ID."""
        options = options or QueryOptions()
        query = self._build_query(options).where(self._model.id == id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(self, options: QueryOptions | None = None) -> list[T]:
        """Get multiple records."""
        options = options or QueryOptions()
        query = self._build_query(options)
        if options.limit:
            query = query.limit(options.limit)
        if options.offset:
            query = query.offset(options.offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_paginated(self, page: int = 1, per_page: int = 20, options: QueryOptions | None = None) -> PaginatedResult[T]:
        """Get paginated records."""
        options = options or QueryOptions()

        count_query = select(func.count()).select_from(self._model)
        if options.filters:
            conditions = [c for f in options.filters if (c := self._build_filter_condition(f)) is not None]
            if conditions:
                count_query = count_query.where(and_(*conditions))

        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        options.limit = per_page
        options.offset = (page - 1) * per_page
        items = await self.get_multi(options)

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            has_next=page * per_page < total,
            has_prev=page > 1,
        )

    async def update[UpdateSchemaType](self, id: Any, obj_in: UpdateSchemaType) -> T | None:
        """Update a record."""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        for field_name, value in update_data.items():
            if hasattr(db_obj, field_name):
                setattr(db_obj, field_name, value)

        await self._session.commit()
        await self._session.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> bool:
        """Delete a record."""
        db_obj = await self.get(id)
        if not db_obj:
            return False
        await self._session.delete(db_obj)
        await self._session.commit()
        return True

    async def bulk_create[CreateSchemaType](self, objs_in: list[CreateSchemaType]) -> list[T]:
        """Create multiple records."""
        db_objs = []
        for obj_in in objs_in:
            data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
            db_objs.append(self._model(**data))

        self._session.add_all(db_objs)
        await self._session.commit()
        for db_obj in db_objs:
            await self._session.refresh(db_obj)
        return db_objs

    async def bulk_update(self, updates: list[dict[str, Any]]) -> int:
        """Bulk update records."""
        if not updates:
            return 0
        stmt = update(self._model)
        result = await self._session.execute(stmt, updates)
        await self._session.commit()
        return result.rowcount

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Bulk delete records."""
        if not ids:
            return 0
        stmt = delete(self._model).where(self._model.id.in_(ids))
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    async def exists(self, id: Any) -> bool:
        """Check if record exists."""
        query = select(func.count()).select_from(self._model).where(self._model.id == id)
        result = await self._session.execute(query)
        return (result.scalar() or 0) > 0

    async def count(self, options: QueryOptions | None = None) -> int:
        """Count records matching criteria."""
        options = options or QueryOptions()
        query = select(func.count()).select_from(self._model)
        if options.filters:
            conditions = [c for f in options.filters if (c := self._build_filter_condition(f)) is not None]
            if conditions:
                query = query.where(and_(*conditions))
        result = await self._session.execute(query)
        return result.scalar() or 0
