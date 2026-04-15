# Deployment Notes

This document captures the intended deployment flow aligned with the architecture roadmap.

## Production compose

From repository root:

```powershell
docker compose -f docker-compose.prod.yml up --build -d
```

Services:
- Nginx entrypoint: port 80
- Backend and frontend are internal behind nginx.

Endpoints via nginx:
- Frontend: `http://localhost/`
- API docs: `http://localhost/docs`

## Railway outline

1. Create project in Railway.
2. Provision PostgreSQL and Redis plugins.
3. Set environment variables from `.env.example`.
4. Deploy backend and frontend services.

## Environment checklist

- DATABASE_URL
- REDIS_URL
- MINIO_ENDPOINT
- MINIO_ACCESS_KEY
- MINIO_SECRET_KEY
- MINIO_BUCKET
- SECRET_KEY
- ALGORITHM
- ACCESS_TOKEN_EXPIRE_MINUTES

## Post-deploy checks

- Backend health: `GET /`
- API docs: `GET /docs`
- Frontend route loads and can call `/api/v1/*` endpoints
