# GraphQL API Documentation

## Overview

Python API Base provides a GraphQL API for flexible data querying.

## Endpoint

```
POST /graphql
```

## Authentication

Include JWT token in Authorization header:

```
Authorization: Bearer <access_token>
```

## Schema

### Queries

```graphql
type Query {
  user(id: ID!): User
  users(page: Int, pageSize: Int): UserConnection!
  item(id: ID!): Item
  items(page: Int, pageSize: Int): ItemConnection!
}
```

### Mutations

```graphql
type Mutation {
  createUser(input: CreateUserInput!): User!
  updateUser(id: ID!, input: UpdateUserInput!): User!
  deleteUser(id: ID!): Boolean!
  createItem(input: CreateItemInput!): Item!
  updateItem(id: ID!, input: UpdateItemInput!): Item!
  deleteItem(id: ID!): Boolean!
}
```

### Types

```graphql
type User {
  id: ID!
  email: String!
  name: String!
  isActive: Boolean!
  createdAt: DateTime!
  items: [Item!]!
}

type Item {
  id: ID!
  name: String!
  description: String
  price: Float!
  owner: User!
  createdAt: DateTime!
}
```

## Example Queries

### Get User with Items

```graphql
query GetUser($id: ID!) {
  user(id: $id) {
    id
    email
    name
    items {
      id
      name
      price
    }
  }
}
```

### Create Item

```graphql
mutation CreateItem($input: CreateItemInput!) {
  createItem(input: $input) {
    id
    name
    price
  }
}
```

## DataLoaders

The API uses DataLoaders to batch and cache database queries, preventing N+1 query problems.

## Related

- [REST API](../rest/index.md)
- [Authentication](../security.md)
