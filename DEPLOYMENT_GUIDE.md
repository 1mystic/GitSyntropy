# GitHub Actions Deployment Guide

This guide explains how to set up GitHub Actions to automatically deploy your GitSyntropy application.

## Overview

The project has two components that need deployment:
- **Backend**: FastAPI application deployed to Railway.io
- **Frontend**: Astro/React application (typically deployed to Vercel, Netlify, or Railway)

---

## Step 1: Add GitHub Secrets

GitHub Secrets are encrypted environment variables stored at the repository level. They're used in workflows without exposing sensitive data.

### How to Add Secrets:

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### Required Secrets for Backend (FastAPI):

| Secret Name | Value | Where to Get |
|---|---|---|
| `GS_DATABASE_URL` | PostgreSQL connection string | Railway.io database plugin or Supabase connection string (format: `postgresql+asyncpg://user:password@host:port/db`) |
| `GS_ANTHROPIC_API_KEY` | Your Anthropic Claude API key | [console.anthropic.com](https://console.anthropic.com) |
| `GS_GITHUB_CLIENT_ID` | GitHub OAuth app Client ID | GitHub app settings |
| `GS_GITHUB_CLIENT_SECRET` | GitHub OAuth app Secret | GitHub app settings (⚠️ SENSITIVE) |
| `GS_GITHUB_ACCESS_TOKEN` | GitHub Personal Access Token | [github.com/settings/tokens](https://github.com/settings/tokens) (needs `repo`, `user`, `read:org` scopes) |
| `GS_JWT_SECRET` | Random secret for JWT signing (32+ chars) | Generate: `openssl rand -hex 32` |
| `GS_FRONTEND_URL` | Your production frontend URL | e.g., `https://yourdomain.com` or Vercel deployment URL |

### Optional Secrets (if deploying frontend to Vercel):

| Secret Name | Value |
|---|---|
| `VERCEL_TOKEN` | Vercel API Token from [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | Your Vercel workspace ID |
| `VERCEL_PROJECT_ID` | Your Vercel project ID for frontend |

### Optional Secrets (if using Railway):

| Secret Name | Value |
|---|---|
| `RAILWAY_TOKEN` | Railway API token from [railway.app/account/tokens](https://railway.app/account/tokens) |

---

## Step 2: Understand Environment Variables

Your application reads these environment variables:

### Backend (.env or GitHub Secrets):
```bash
GS_APP_NAME=GitSyntropy API
GS_DATABASE_URL=postgresql+asyncpg://...
GS_ANTHROPIC_API_KEY=sk-...
GS_GITHUB_CLIENT_ID=your-github-client-id
GS_GITHUB_CLIENT_SECRET=your-github-client-secret
GS_GITHUB_ACCESS_TOKEN=ghp_...
GS_JWT_SECRET=your-random-jwt-secret
GS_JWT_ALGORITHM=HS256
GS_JWT_EXP_MINUTES=60
GS_FRONTEND_URL=https://yourdomain.com
```

### Frontend (.env or `astro.config.mjs`):
```bash
PUBLIC_API_BASE=https://api.yourdomain.com/api/v1
PUBLIC_API_URL=https://api.yourdomain.com/api/v1
```

---

## Step 3: Create a Deployment Workflow

Create or update `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:  # Allow manual trigger

jobs:
  deploy-backend:
    name: Deploy Backend to Railway
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: ./.github/actions/railway-deploy
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend
        env:
          GS_DATABASE_URL: ${{ secrets.GS_DATABASE_URL }}
          GS_ANTHROPIC_API_KEY: ${{ secrets.GS_ANTHROPIC_API_KEY }}
          GS_GITHUB_CLIENT_ID: ${{ secrets.GS_GITHUB_CLIENT_ID }}
          GS_GITHUB_CLIENT_SECRET: ${{ secrets.GS_GITHUB_CLIENT_SECRET }}
          GS_GITHUB_ACCESS_TOKEN: ${{ secrets.GS_GITHUB_ACCESS_TOKEN }}
          GS_JWT_SECRET: ${{ secrets.GS_JWT_SECRET }}
          GS_FRONTEND_URL: ${{ secrets.GS_FRONTEND_URL }}

  deploy-frontend:
    name: Deploy Frontend to Vercel
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        working-directory: apps/frontend
        run: npm ci

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: apps/frontend
          scope: your-vercel-org
        env:
          PUBLIC_API_BASE: ${{ secrets.GS_FRONTEND_API_URL }}
```

---

## Step 4: Configure Your Deployment Platforms

### Option A: Railway + Vercel (Recommended)

#### Railway Backend Setup:
1. Initialize your project: `railway init` (or use Railway dashboard)
2. Link your GitHub repository
3. Create a PostgreSQL plugin in Railway
4. Set environment variables in Railway dashboard
5. `railway.toml` already configured (see apps/backend/railway.toml)

#### Vercel Frontend Setup:
1. Import project from GitHub: [vercel.com/new](https://vercel.com/new)
2. Select `apps/frontend` as root directory
3. Set Environment Variables:
   - `PUBLIC_API_URL` → `https://your-railway-backend-url/api/v1`
4. Deploy

### Option B: Railway for Both

```yaml
# Backend: already configured via railway.toml
# Frontend: would need a custom start command

# Create apps/frontend/railway.toml:
[build]
builder = "nixpacks"

[build.env]
NIXPACKS_NODE_VERSION = "20"

[deploy]
startCommand = "npm run preview"
```

---

## Step 5: Set Up GitHub OAuth app

1. Go to GitHub Settings → Developer settings → [OAuth apps](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: GitSyntropy
   - **Homepage URL**: `https://yourdomain.com`
   - **Authorization callback URL**: `https://yourdomain.com/auth` (or your API auth callback)
4. Copy **Client ID** and **Client Secret** → add to GitHub Secrets

---

## Step 6: Database Setup

### Option A: Railway PostgreSQL
- Add PostgreSQL plugin in Railway dashboard
- Copy connection string to `GS_DATABASE_URL` secret

### Option B: Supabase
1. Create project at [supabase.com](https://supabase.com)
2. Go to Project Settings → Database
3. Copy **Connection string** (PostgreSQL URL)
4. Add to GitHub Secrets as `GS_DATABASE_URL`

---

## Step 7: Test the Workflow

Create a test deployment:
```bash
# Push to main branch to trigger workflow
git commit --allow-empty -m "trigger deployment"
git push origin main
```

Monitor at: **GitHub Repo → Actions → select workflow run**

---

## Troubleshooting

### Workflow Fails with "missing secret"
- Verify secret name exactly matches (case-sensitive)
- Check it's in the correct repo, not organization

### API calls fail in production
- Verify `GS_FRONTEND_URL` matches your actual frontend domain
- Check `PUBLIC_API_URL` in frontend is correct
- Ensure backend secrets are set in deployment platform

### Database connection fails
- Test connection string locally: 
  ```bash
  psql postgresql+asyncpg://user:pass@host:port/db
  ```
- Verify IP whitelisting if using Supabase (add Railway IP to allowlist)

### CORS errors
- Add production domain to backend CORS settings
- Update `GS_FRONTEND_URL` in backend

---

## Verification Checklist

- [ ] All secrets added to GitHub
- [ ] Database URL set correctly
- [ ] GitHub OAuth app created and secrets added
- [ ] Claude API key set
- [ ] JWT secret generated and set
- [ ] Frontend API URL environment variable configured
- [ ] GitHub Action workflow runs without errors
- [ ] Backend health check passes: `GET /api/v1/health`
- [ ] Frontend builds successfully
- [ ] OAuth login flow works end-to-end

---

## Security Best Practices

1. **Never commit secrets** to version control
2. **Rotate JWT secret** periodically
3. **Use GitHub token** with minimal required scopes
4. **Enable branch protection** requiring status checks
5. **Audit secret access** in GitHub Settings → Audit log
6. **Restrict deployment** to specific branches (e.g., `main`)
7. **Enable HTTPS** on all domains

---

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Railway Deployment Guide](https://docs.railway.app/deploy/githubconnection)
- [Vercel GitHub Integration](https://vercel.com/docs/deployments/git)
- [Supabase Database Setup](https://supabase.com/docs/guides/database)
- [Anthropic API Keys](https://console.anthropic.com)

