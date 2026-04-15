# Deployment Guide: Render Backend + Vercel Frontend

This guide walks you through deploying ApexS publicly on Render (backend Docker) and Vercel (frontend static).

## Step 1: Commit and Push Code to GitHub

From your local machine:

```bash
cd /home/madhan/Documents/GitHub/SE
git add .
git commit -m "Deploy: Backend on Render, Frontend on Vercel"
git push origin main
```

Verify push succeeded:
- Open https://github.com/madhan-karthikeyan/ApexS_SWE
- Confirm you see your latest commit on the main branch

---

## Step 2: Deploy Backend on Render

### 2.1 Create Render Service

1. Go to https://render.com and sign in (create account if needed)
2. Click **New +** → **Web Service**
3. Click **Connect a repository**
   - Search for `ApexS_SWE`
   - Connect it
4. Fill in service details:
   - **Name**: `apexs-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Branch**: `main`
5. Click **Create Web Service**

### 2.2 Configure Backend Environment

The service will start building. While building, set environment variables:

1. In the Render dashboard, go to your `apexs-backend` service
2. Click **Environment** tab
3. Add these variables (exact values):

```
DATABASE_URL=sqlite:///./apexs.db
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=datasets
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
USE_CELERY=false
ALLOW_THREAD_FALLBACK=true
ENFORCE_AUTH=false
CORS_ORIGINS=https://your-vercel-frontend-domain.vercel.app
```

4. Replace `https://your-vercel-frontend-domain.vercel.app` with your actual Vercel domain (you'll set this in Step 3)

### 2.3 Verify Backend Deployed

Wait for build to complete, then:

1. Copy the public URL (e.g., `https://apexs-backend.onrender.com`)
2. Open `https://apexs-backend.onrender.com/health` in browser
3. You should see JSON response:
   ```json
   {
     "status": "ok",
     "checks": {...},
     "uptime_seconds": 123,
     "request_count": 5
   }
   ```

**Save this backend URL** — you'll need it for frontend.

---

## Step 3: Deploy Frontend on Vercel

### 3.1 Import Repository to Vercel

1. Go to https://vercel.com and sign in (create account if needed)
2. Click **Add New...** → **Project**
3. Click **Import Git Repository**
   - Search for `ApexS_SWE`
   - Import it
4. Configure project:
   - **Project Name**: `apexs-frontend`
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
5. Click **Import**

### 3.2 Set Frontend Environment Variables

Before deployment completes, add environment variables:

1. In Vercel project settings, go to **Settings** → **Environment Variables**
2. Add these variables:

```
VITE_API_BASE_URL=https://apexs-backend.onrender.com
VITE_ALLOWED_HOSTS=your-frontend.vercel.app
```

Replace with your actual:
- Backend URL from Step 2.3
- Frontend domain (shown after deployment)

3. Click **Save**
4. Go to **Deployments** and click **Redeploy** on the latest deployment to apply env vars

### 3.3 Verify Frontend Deployed

After redeploy completes:

1. Copy the Vercel public URL (e.g., `https://apexs-frontend.vercel.app`)
2. Open it in browser
3. You should see the ApexS dashboard

---

## Step 4: Update Backend CORS After Frontend Domain Known

Now that you have the Vercel frontend URL:

1. Go to Render backend service
2. Go to **Environment** tab
3. Update `CORS_ORIGINS` to match your actual Vercel domain:
   ```
   CORS_ORIGINS=https://apexs-frontend.vercel.app
   ```
4. Click **Save**
5. Service auto-redeploys with new CORS setting

---

## Step 5: End-to-End Smoke Test

### 5.1 Backend Health Check

```bash
curl https://apexs-backend.onrender.com/health
curl https://apexs-backend.onrender.com/docs
```

Both should return 200 OK.

### 5.2 Frontend Workflow Test

1. Open https://apexs-frontend.vercel.app in browser
2. Dashboard should load
3. Click **Upload Dataset** and upload a sample CSV
4. Click **Configure Sprint** and set capacity/goals
5. Click **Generate Plan**
6. Wait for status to show "done"
7. Click **Review Explanations**
8. Click **Approve & Export**

If all steps work: **Deployment successful!**

---

## Step 6: Known Limitations on Free Tier

1. **Render free instance sleeps** — first request after inactivity is slow (~30s)
2. **SQLite not durable** — data resets on service restart/redeploy
3. **No async queue** — planning jobs run in-process (acceptable for demo)

---

## Troubleshooting

### Backend won't start
- Check Render build logs for Python dependency errors
- Verify backend/Dockerfile exists
- Verify backend/requirements.txt has all dependencies

### Frontend won't load frontend
- Check Vercel build logs for npm errors
- Verify frontend/package.json exists
- Verify VITE_API_BASE_URL is set to exact backend URL

### Frontend API calls fail
- Open browser console (F12 → Console)
- Check for CORS errors
- Verify backend CORS_ORIGINS matches frontend domain exactly
- Verify VITE_API_BASE_URL in frontend is reachable

### Plan generation stuck
- Set `USE_CELERY=false` and `ALLOW_THREAD_FALLBACK=true` on backend (default in this guide)
- Check backend logs for planning errors

---

## Next Steps (After Validation)

1. Replace SQLite with Neon postgres + R2 storage for durability
2. Add Redis and re-enable Celery for real job queueing
3. Upgrade Render plan from free to paid for always-on instance
4. Set `ENFORCE_AUTH=true` and create login flow

---

## Reference Files in Repository

- `backend/Dockerfile` — backend container build
- `backend/requirements.txt` — Python dependencies
- `backend/app/core/config.py` — runtime environment settings
- `frontend/package.json` — frontend dependencies
- `frontend/vite.config.ts` — frontend build and proxy config
- `frontend/src/utils/api.ts` — frontend API base URL wiring
