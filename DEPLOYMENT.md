# Deployment Guide

## Overview
- **Backend**: FastAPI + NeuralFoil on Railway
- **Frontend**: React + Vite + Three.js on Vercel

---

## 🚂 Backend Deployment (Railway)

### Prerequisites
- Railway account: https://railway.app
- Railway CLI (optional): `npm install -g @railway/cli`

### Files Created
- ✅ `backend/Procfile` - Deployment command
- ✅ `backend/railway.json` - Railway configuration
- ✅ Backend ready for deployment

### Deploy to Railway

#### Option 1: Web UI (Recommended)
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Set root directory to `backend`
5. Railway will auto-detect Python and deploy

#### Option 2: Railway CLI
```bash
cd backend
railway login
railway init
railway up
```

### Required Environment Variables on Railway

Set these in Railway Dashboard → Variables:

```bash
# Application
APP_NAME=AirfoilLearner
ENV=production
DEBUG=False
API_V1_PREFIX=/api/v1

# Server (Railway sets PORT automatically)
HOST=0.0.0.0

# CORS - ADD YOUR VERCEL URL!
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:5173"]

# AI APIs (Required for chat/agent features)
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=anthropic
AI_MODEL=claude-3-5-sonnet-20241022

# Optional (only if using these features)
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=your-secret-key-change-me
```

### After Deployment
1. Railway will provide a URL like: `https://your-app.up.railway.app`
2. Test health endpoint: `https://your-app.up.railway.app/health`
3. Copy this URL for frontend configuration

---

## ▲ Frontend Deployment (Vercel)

### Prerequisites
- Vercel account: https://vercel.com
- Vercel CLI (optional): `npm install -g vercel`

### Files Created
- ✅ `frontend/vercel.json` - Vercel configuration
- ✅ `frontend/.env.example` - Environment template
- ✅ `frontend/.env.production` - Production template
- ✅ Updated `RightPanel.jsx` to use env variables

### Deploy to Vercel

#### Option 1: Web UI (Recommended)
1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Set root directory to `frontend`
4. Framework preset: Vite
5. Add environment variable (see below)
6. Click "Deploy"

#### Option 2: Vercel CLI
```bash
cd frontend
vercel login
vercel --prod
```

### Required Environment Variables on Vercel

Set in Vercel Dashboard → Settings → Environment Variables:

```bash
VITE_API_URL=https://your-backend.up.railway.app/api/v1
```

**IMPORTANT**: After setting `VITE_API_URL`, redeploy the frontend for changes to take effect.

### After Deployment
1. Vercel will provide a URL like: `https://your-app.vercel.app`
2. Test the app in your browser

---

## 🔗 Connecting Frontend & Backend

### Step 1: Deploy Backend First
1. Deploy backend to Railway
2. Copy the Railway URL: `https://your-app.up.railway.app`

### Step 2: Update Backend CORS
In Railway environment variables, update `CORS_ORIGINS`:
```bash
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:5173"]
```

### Step 3: Configure Frontend
In Vercel environment variables, set:
```bash
VITE_API_URL=https://your-app.up.railway.app/api/v1
```

### Step 4: Redeploy Frontend
After adding the environment variable, trigger a new deployment on Vercel.

---

## 🧪 Testing Deployment

### Backend Health Check
```bash
curl https://your-backend.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "agent": "FREE",
  "cfd": "NeuralFoil",
  "features": ["agent", "simulations", "chat", "challenges"]
}
```

### Frontend Test
1. Visit: `https://your-frontend.vercel.app`
2. Open browser console (F12)
3. Send a test message in the chat
4. Check that API calls go to your Railway URL

---

## 📋 Deployment Checklist

### Backend (Railway)
- [ ] Repository connected to Railway
- [ ] Root directory set to `backend`
- [ ] All required environment variables added
- [ ] `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` set
- [ ] Health endpoint responding: `/health`
- [ ] Deployment successful

### Frontend (Vercel)
- [ ] Repository connected to Vercel
- [ ] Root directory set to `frontend`
- [ ] `VITE_API_URL` environment variable set
- [ ] Frontend redeployed after env var change
- [ ] Can access the app in browser

### Connection
- [ ] Backend CORS includes Vercel URL
- [ ] Frontend API calls use correct Railway URL
- [ ] Chat functionality works end-to-end
- [ ] Simulations can be triggered

---

## 🐛 Troubleshooting

### CORS Errors
**Problem**: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution**:
1. Check Railway `CORS_ORIGINS` includes your Vercel URL
2. Format: `["https://your-app.vercel.app"]` (JSON array)
3. Redeploy backend after changing CORS

### API Connection Fails
**Problem**: Frontend can't reach backend

**Solution**:
1. Verify `VITE_API_URL` in Vercel env vars
2. Ensure URL includes `/api/v1` at the end
3. Redeploy frontend after changing env vars
4. Check browser console for actual API URL being used

### Build Failures

**Backend**:
- Check `requirements.txt` is present
- Verify Python version compatibility
- Check Railway build logs

**Frontend**:
- Verify `package.json` build script exists
- Check for missing dependencies
- Check Vercel build logs

### Chat Not Working
**Problem**: Chat sends messages but gets errors

**Solution**:
1. Check `ANTHROPIC_API_KEY` is set in Railway
2. Verify API key is valid
3. Check Railway logs for detailed errors
4. Ensure backend `/health` endpoint works

---

## 🔄 Redeployment

### Backend
Railway auto-deploys on git push to main branch.

Manual redeploy:
```bash
railway up
```

### Frontend
Vercel auto-deploys on git push to main branch.

Manual redeploy:
```bash
vercel --prod
```

---

## 💰 Cost Estimates

### Railway (Backend)
- **Free Tier**: $5 credit/month (500 hours)
- **Hobby**: $5/month (unlimited hours)
- Estimated usage: Should fit in free tier for development

### Vercel (Frontend)
- **Hobby**: Free
- **Pro**: $20/month (if needed)
- Free tier is sufficient for most projects

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [Vercel Documentation](https://vercel.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)

---

## 🎉 Success!

Your app is now deployed:
- **Backend**: https://your-backend.up.railway.app
- **Frontend**: https://your-frontend.vercel.app
- **API Docs**: https://your-backend.up.railway.app/docs

Next steps:
1. Set up custom domain (optional)
2. Configure monitoring/logging
3. Set up CI/CD pipelines
4. Add analytics
