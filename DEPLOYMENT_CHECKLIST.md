# Deployment Readiness Checklist

Complete this checklist before starting deployment on Render + Vercel.

## Pre-Deployment (Local)

- [ ] All code changes committed to `main` branch
- [ ] Git remote configured: `git remote -v` shows `https://github.com/madhan-karthikeyan/ApexS_SWE.git`
- [ ] Latest code pushed to GitHub: `git push origin main`
- [ ] Dockerfile files exist:
  - [ ] `backend/Dockerfile` (Python 3.11 + FastAPI)
  - [ ] `frontend/Dockerfile` (Node 20 + Vite build)
- [ ] Environment config ready:
  - [ ] `backend/app/core/config.py` supports `CORS_ORIGINS` and `USE_CELERY` env vars
  - [ ] `frontend/src/utils/api.ts` uses `VITE_API_BASE_URL`
  - [ ] `frontend/vite.config.ts` loads env vars properly

## Render Setup

- [ ] Render account created at https://render.com
- [ ] GitHub connected to Render
- [ ] Backend service created with:
  - [ ] Root Directory: `backend`
  - [ ] Runtime: Docker
  - [ ] All env vars set (see deployment guide)
- [ ] Backend deployed and `/health` endpoint responds
- [ ] Backend URL saved (e.g., `https://apexs-backend.onrender.com`)

## Vercel Setup

- [ ] Vercel account created at https://vercel.com
- [ ] GitHub connected to Vercel
- [ ] Frontend project created with:
  - [ ] Root Directory: `frontend`
  - [ ] Framework: Vite
  - [ ] All env vars set (see deployment guide)
  - [ ] `VITE_API_BASE_URL` points to Render backend
- [ ] Frontend deployed
- [ ] Frontend URL saved (e.g., `https://apexs-frontend.vercel.app`)

## Post-Deployment Validation

- [ ] Backend `/health` endpoint returns 200 OK
- [ ] Backend `/docs` endpoint loads (Swagger UI)
- [ ] Frontend loads without errors
- [ ] Frontend dashboard shows "System Ready" badge
- [ ] CORS works: frontend can call backend `/api/v1/*` endpoints
- [ ] Full workflow works:
  - [ ] Upload dataset succeeds
  - [ ] Configure sprint succeeds
  - [ ] Generate plan completes (status = "done")
  - [ ] Explanations load
  - [ ] Export works

## Go-Live

- [ ] Backend `CORS_ORIGINS` updated to exact frontend domain
- [ ] Both services redeploy successfully
- [ ] All validation tests pass
- [ ] Ready to share public URLs with users

---

Use the detailed guide in `DEPLOYMENT_RENDER_VERCEL.md` for step-by-step instructions.
