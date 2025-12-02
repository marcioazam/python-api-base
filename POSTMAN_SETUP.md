# Postman Setup Guide

Complete guide to test the Python API Base using Postman.

## Files

- **Python-API-Base.postman_collection.json** - API collection with all endpoints
- **Python-API-Base.postman_environment.json** - Environment variables for local development

## Quick Start

### 1. Import Collection and Environment

1. Open Postman
2. Click **Import** (top-left)
3. Select **Python-API-Base.postman_collection.json**
4. Click **Import** again
5. Repeat for **Python-API-Base.postman_environment.json**

### 2. Select Environment

1. Top-right dropdown, select **Python API Base - Local Development**
2. Verify `base_url` is set to `http://localhost:8000`

### 3. Start API Server

```bash
# From project root
docker-compose -f deployments/docker/docker-compose.example.yml up -d

# Or run locally
export DEBUG=false
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing Workflow

### Step 1: Check Health

1. Go to **Health Check** folder
2. Run **Health - Live** (GET /health/live)
3. Should return 200 OK

### Step 2: Login

1. Go to **Authentication** folder
2. Run **Login** (POST /api/v1/auth/login)
   - Uses `admin@example.com` / `Admin123!`
   - **Auto-saves** `access_token` to environment
3. Check response - should have `access_token`

### Step 3: Test User Endpoints

1. Go to **Users Management** folder
2. Run **List All Users** (GET /api/v1/users)
   - Should return list of users
3. Run **Get User by ID** (GET /api/v1/users/{user_id})
   - Uses `{{user_id}}` variable
4. Run **List All Roles** (GET /api/v1/users/roles/list)
   - Shows available roles: admin, user, viewer, moderator

### Step 4: Test Examples

1. Go to **Examples - Items** folder
2. Run **Create Item** (POST /api/v1/examples/items)
   - Creates a new item
   - Copy ID to `item_id` variable
3. Run **Get Item by ID** (GET /api/v1/examples/items/{item_id})
4. Run **Update Item** (PATCH /api/v1/examples/items/{item_id})
5. Run **Delete Item** (DELETE /api/v1/examples/items/{item_id})

## Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `base_url` | http://localhost:8000 | API base URL |
| `access_token` | (auto-filled) | JWT token from login |
| `refresh_token` | (auto-filled) | Refresh token |
| `user_id` | (manual) | User ID for operations |
| `item_id` | (manual) | Item ID for operations |
| `pedido_id` | (manual) | Order ID for operations |
| `admin_email` | admin@example.com | Default admin email |
| `admin_password` | Admin123! | Default admin password |

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (saves token)
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - Logout

### Users
- `GET /api/v1/users` - List users (paginated)
- `GET /api/v1/users/{user_id}` - Get user
- `PATCH /api/v1/users/{user_id}` - Update user
- `POST /api/v1/users/{user_id}/roles` - Assign role
- `DELETE /api/v1/users/{user_id}/roles/{role_name}` - Revoke role
- `GET /api/v1/users/roles/list` - List all roles

### Items (Example)
- `GET /api/v1/examples/items` - List items
- `POST /api/v1/examples/items` - Create item
- `GET /api/v1/examples/items/{item_id}` - Get item
- `PATCH /api/v1/examples/items/{item_id}` - Update item
- `DELETE /api/v1/examples/items/{item_id}` - Delete item

### Orders (Example)
- `GET /api/v1/examples/pedidos` - List orders
- `POST /api/v1/examples/pedidos` - Create order
- `GET /api/v1/examples/pedidos/{pedido_id}` - Get order
- `POST /api/v1/examples/pedidos/{pedido_id}/items` - Add item to order
- `POST /api/v1/examples/pedidos/{pedido_id}/confirm` - Confirm order
- `POST /api/v1/examples/pedidos/{pedido_id}/cancel` - Cancel order

### Health
- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness check

## Default Credentials

**Admin User:**
- Email: `admin@example.com`
- Password: `Admin123!`

**Available Roles:**
- `admin` - Full system access
- `user` - Standard user access
- `viewer` - Read-only access
- `moderator` - Content moderation

## Tips

1. **Auto-save tokens**: Login request automatically saves `access_token` to environment
2. **Bearer token**: All authenticated endpoints use `Authorization: Bearer {{access_token}}`
3. **Pagination**: List endpoints support `page` and `page_size` query parameters
4. **Error handling**: Check response status codes and error messages
5. **Test order**: Follow the workflow above for best results

## Troubleshooting

### 401 Unauthorized
- Token expired: Run Login again
- Wrong token: Check `access_token` variable in environment

### 404 Not Found
- Endpoint doesn't exist: Check URL in collection
- Resource not found: Verify ID variables are set

### 500 Internal Server Error
- Check server logs: `docker-compose logs api`
- Verify database is running: `docker-compose ps`

### Connection Refused
- API not running: Start with `docker-compose up -d`
- Wrong port: Verify `base_url` is `http://localhost:8000`

## Docker Commands

```bash
# Start services
docker-compose -f deployments/docker/docker-compose.example.yml up -d

# View logs
docker-compose -f deployments/docker/docker-compose.example.yml logs -f api

# Stop services
docker-compose -f deployments/docker/docker-compose.example.yml down

# Reset database
docker-compose -f deployments/docker/docker-compose.example.yml down -v
docker-compose -f deployments/docker/docker-compose.example.yml up -d
```

## Documentation

- API Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

---

**Created:** 2024-12-01  
**Last Updated:** 2024-12-01  
**API Version:** 2025
