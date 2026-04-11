# GitHub Secrets Setup Template

Use this as a checklist when configuring secrets in your GitHub repository.

## Step-by-Step Setup

Go to: **GitHub Repository → Settings → Secrets and variables → Actions**

Click **New repository secret** for each item below:

---

## ✅ REQUIRED SECRETS

### Backend Database Credentials
**Secret Name:** `GS_DATABASE_URL`
**Example:** `postgresql+asyncpg://postgres:password@db.railway.internal:5432/gitsyntropy`
**Where to get it:**
- If using Railway: Railway Dashboard → PostgreSQL Plugin → Connection String
- If using Supabase: Supabase Dashboard → Settings → Database → Connection String (PostgreSQL)

---

### Claude API Key (Anthropic)
**Secret Name:** `GS_ANTHROPIC_API_KEY`
**Example:** `sk-ant-v0-...` (starts with `sk-ant-v0`)
**Where to get it:** [console.anthropic.com](https://console.anthropic.com) → Create API Key

---

### GitHub OAuth Credentials
**Secret Name:** `GS_GITHUB_CLIENT_ID`
**Example:** `Iv1.abc123def456` (about 20 chars)
**Where to get it:**
1. Go to GitHub Settings → Developer settings → [OAuth Apps](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in:
   - **Application name:** GitSyntropy
   - **Homepage URL:** `https://yourdomain.com`  
   - **Authorization callback URL:** `https://yourdomain.com/auth` (add to your backend redirect logic)
4. Copy **Client ID**

---

**Secret Name:** `GS_GITHUB_CLIENT_SECRET`
**Example:** `ghclient_secret_abcd1234efgh5678ijkl9012` (long string)
**Where to get it:** Same OAuth App page, copy **Client Secret** (⚠️ Keep this secret!)

---

### GitHub Personal Access Token
**Secret Name:** `GS_GITHUB_ACCESS_TOKEN`
**Example:** `ghp_abcDefgHijKlMnOpQrStUvWxYz1234567890`
**Where to get it:**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it: `GitSyntropy Backend`
4. Select scopes:
   - ✅ `repo` (full control of private repositories)
   - ✅ `user` (read user profile data)
   - ✅ `read:org` (read organization data)
5. Copy token and add to secrets

---

### JWT Signing Secret
**Secret Name:** `GS_JWT_SECRET`
**Example:** `a3f8b2c9d1e4f7g6h5i8j2k1l4m7n9o2p5q8r1s4t7u0v3w6x9y2z5` (32+ random characters)
**How to generate:**
```bash
# On Mac/Linux:
openssl rand -hex 32

# On Windows (using Git Bash):
openssl rand -hex 32

# Or use an online tool: 
# https://www.lastpass.com/features/password-generator
```

---

## 🔐 DEPLOYMENT PLATFORM CREDENTIALS

### Railway Deployment Token (if using Railway)
**Secret Name:** `RAILWAY_TOKEN`
**Where to get it:** [railway.app/account/tokens](https://railway.app/account/tokens)
**How to use:** Required for GitHub Actions to deploy to Railway

---

### Vercel Deployment Tokens (if using Vercel for frontend)
**Secret Name:** `VERCEL_TOKEN`
**Where to get it:** [vercel.com/account/tokens](https://vercel.com/account/tokens)
**Scope:** Select "Full Account"

---

**Secret Name:** `VERCEL_ORG_ID`
**Where to get it:**
1. Go to Vercel Dashboard
2. Go to Account Settings → General
3. Copy **Team ID**

---

**Secret Name:** `VERCEL_PROJECT_ID`
**Where to get it:**
1. Go to your project settings in Vercel
2. Copy **Project ID**

---

## 🔗 ENVIRONMENT & URL SECRETS

### Production URLs
**Secret Name:** `PUBLIC_API_URL_PROD`
**Example:** `https://api.yourdomain.com/api/v1` or `https://gitsyntropy-backend-prod.railway.app/api/v1`
**Purpose:** Frontend needs to know where the API is (used during build)

---

**Secret Name:** `GS_FRONTEND_URL`
**Example:** `https://yourdomain.com` or `https://gitsyntropy.vercel.app`
**Purpose:** Backend uses this to set CORS and OAuth redirect URLs

---

**Secret Name:** `BACKEND_URL`
**Example:** `https://api.yourdomain.com` or `https://gitsyntropy-backend-prod.railway.app`
**Purpose:** Used in health checks after deployment

---

**Secret Name:** `FRONTEND_URL`
**Example:** `https://yourdomain.com` or `https://gitsyntropy.vercel.app`
**Purpose:** Notification & deployment verification

---

## 📢 OPTIONAL: NOTIFICATIONS

### Slack Webhook (for deployment notifications)
**Secret Name:** `SLACK_WEBHOOK`
**Where to get it:**
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create New App → From scratch
3. Enable "Incoming Webhooks"
4. Add New Webhook to Workspace
5. Copy the URL

---

## 🚀 Quick Verification

After adding all secrets, verify they're set:

```bash
# You can't view secret values, but check they exist:
# In GitHub UI, go to Settings → Secrets and verify all are listed
```

Run a test deployment:
```bash
git commit --allow-empty -m "test deployment"
git push origin main
```

Check the workflow: **GitHub → Actions → Latest run**

---

## ⚠️ Security Checklist

- [ ] Never commit secrets to version control
- [ ] Rotate `GS_JWT_SECRET` every 90 days
- [ ] Use different secrets for staging vs production
- [ ] Enable branch protection requiring checks pass before merge
- [ ] Audit GitHub secret access in Settings → Audit log
- [ ] Use minimum required OAuth app scopes
- [ ] Regenerate tokens if compromised

---

## 🔧 Troubleshooting

**"Error: secret not found"** → Double-check secret name is EXACT (case-sensitive)

**"Deployment fails with API errors"** → Verify `PUBLIC_API_URL_PROD` matches your actual backend URL

**"CORS errors in frontend"** → Ensure `GS_FRONTEND_URL` matches your domain exactly

**"GitHub OAuth fails"** → Verify callback URL in OAuth app matches `yourdomain.com/auth`

