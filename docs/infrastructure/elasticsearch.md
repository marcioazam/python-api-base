# Elasticsearch Integration

## Overview

Elasticsearch é usado para busca full-text e analytics.

## Configuration

```bash
ELASTICSEARCH__URL=http://localhost:9200
ELASTICSEARCH__INDEX_PREFIX=api
```

## Client Setup

```python
from elasticsearch import AsyncElasticsearch

class ElasticsearchClient:
    def __init__(self, url: str):
        self._client = AsyncElasticsearch([url])
    
    async def close(self) -> None:
        await self._client.close()
```

## Index Management

```python
async def create_index(self, index: str, mappings: dict) -> None:
    """Create index with mappings."""
    if not await self._client.indices.exists(index=index):
        await self._client.indices.create(
            index=index,
            body={"mappings": mappings},
        )

# User index mapping
USER_MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "email": {"type": "keyword"},
        "name": {"type": "text", "analyzer": "standard"},
        "created_at": {"type": "date"},
        "is_active": {"type": "boolean"},
    }
}
```

## Indexing Documents

```python
async def index_document(self, index: str, id: str, document: dict) -> None:
    """Index a single document."""
    await self._client.index(index=index, id=id, body=document)

async def bulk_index(self, index: str, documents: list[dict]) -> None:
    """Bulk index documents."""
    actions = []
    for doc in documents:
        actions.append({"index": {"_index": index, "_id": doc["id"]}})
        actions.append(doc)
    
    await self._client.bulk(body=actions)

async def delete_document(self, index: str, id: str) -> None:
    """Delete a document."""
    await self._client.delete(index=index, id=id, ignore=[404])
```

## Search Operations

```python
async def search(
    self,
    index: str,
    query: dict,
    size: int = 10,
    from_: int = 0,
) -> SearchResult:
    """Execute search query."""
    response = await self._client.search(
        index=index,
        body={"query": query},
        size=size,
        from_=from_,
    )
    
    return SearchResult(
        total=response["hits"]["total"]["value"],
        hits=[hit["_source"] for hit in response["hits"]["hits"]],
    )

# Full-text search
async def search_users(self, query: str) -> list[dict]:
    result = await self.search(
        index="users",
        query={
            "multi_match": {
                "query": query,
                "fields": ["name^2", "email"],
                "fuzziness": "AUTO",
            }
        },
    )
    return result.hits
```

## Query Examples

```python
# Match query
{"match": {"name": "john"}}

# Term query (exact match)
{"term": {"status": "active"}}

# Range query
{"range": {"created_at": {"gte": "2024-01-01"}}}

# Bool query (AND/OR)
{
    "bool": {
        "must": [{"match": {"name": "john"}}],
        "filter": [{"term": {"is_active": True}}],
        "should": [{"match": {"email": "gmail"}}],
    }
}

# Aggregations
{
    "aggs": {
        "status_count": {
            "terms": {"field": "status"}
        }
    }
}
```

## Search Repository

```python
class UserSearchRepository:
    def __init__(self, es: ElasticsearchClient):
        self._es = es
        self._index = "users"
    
    async def index_user(self, user: User) -> None:
        await self._es.index_document(
            self._index,
            user.id,
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            },
        )
    
    async def search(self, query: str, filters: dict | None = None) -> list[dict]:
        bool_query = {
            "must": [{"multi_match": {"query": query, "fields": ["name", "email"]}}],
        }
        
        if filters:
            bool_query["filter"] = [{"term": {k: v}} for k, v in filters.items()]
        
        return await self._es.search(self._index, {"bool": bool_query})
```

## Best Practices

1. **Use appropriate analyzers** - For text fields
2. **Set mappings explicitly** - Don't rely on dynamic mapping
3. **Use bulk operations** - For multiple documents
4. **Monitor cluster health** - Alert on yellow/red status
5. **Set refresh intervals** - Balance freshness vs performance
