# Vercel Deployment

Deploy the Python API Base to Vercel's serverless platform.

## Prerequisites

- Vercel CLI installed (`npm i -g vercel`)
- Vercel account

## Quick Start

```bash
# From project root
cd deployments/serverless/vercel

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

## Configuration

### vercel.json

The `vercel.json` file configures:
- **Python runtime** for the API
- **Routing** to forward all requests to the FastAPI app
- **Memory and timeout** settings
- **Environment variables**

### Environment Variables

Set these in Vercel Dashboard or CLI:

```bash
vercel env add DATABASE__URL
vercel env add SECURITY__SECRET_KEY
vercel env add OBSERVABILITY__REDIS_URL
```

| Variable | Description | Required |
|----------|-------------|----------|
| `ENVIRONMENT` | Set to "vercel" | Auto |
| `DATABASE__URL` | PostgreSQL URL | Yes |
| `SECURITY__SECRET_KEY` | JWT key | Yes |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Vercel Edge Network                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Serverless Function (Python 3.12)                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ FastAPI Application                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Limitations

1. **Cold starts**: ~500ms-2s for Python functions
2. **Max duration**: 30s for Pro, 10s for Hobby
3. **Max size**: 50MB for the function bundle
4. **No persistent connections**: Use connection poolers (PgBouncer)

## Database Considerations

For PostgreSQL, use a serverless-friendly provider:
- **Neon** (recommended): Serverless Postgres
- **Supabase**: Postgres with connection pooling
- **PlanetScale**: MySQL (if switching DBs)

## Local Development

```bash
# Install Vercel CLI
npm i -g vercel

# Link to project
vercel link

# Pull environment variables
vercel env pull .env.local

# Run locally
vercel dev
```

## Monitoring

- Vercel Dashboard for logs and analytics
- Connect to external observability (Datadog, etc.) via environment variables
