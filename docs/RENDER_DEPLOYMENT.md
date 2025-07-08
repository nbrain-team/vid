# 🚀 Render Deployment Guide

This guide walks you through deploying the AI-Powered Media Indexing Platform on Render.

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to GitHub
3. **External Services**:
   - Qdrant Cloud account (free tier available)
   - AWS S3 or compatible storage (MinIO, Backblaze B2, etc.)

## 🏗️ Architecture on Render

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│  Celery Worker  │
│  (Web Service)  │     │  (Web Service)  │     │    (Worker)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌─────────────┐           ┌─────────────┐
                        │ PostgreSQL  │           │    Redis    │
                        │  (Managed)  │           │  (Managed)  │
                        └─────────────┘           └─────────────┘
                               │                          │
                               ▼                          ▼
                        ┌─────────────┐           ┌─────────────┐
                        │ Qdrant Cloud│           │  S3 Storage │
                        │  (External) │           │  (External) │
                        └─────────────┘           └─────────────┘
```

## 📝 Step-by-Step Deployment

### Step 1: Set Up External Services

#### 1.1 Qdrant Cloud Setup
1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a new cluster (free tier available)
3. Note down:
   - Cluster URL (e.g., `xyz-abc.us-east-1-0.aws.cloud.qdrant.io`)
   - API Key

#### 1.2 S3-Compatible Storage Setup

**Option A: AWS S3**
1. Create an S3 bucket
2. Create IAM user with S3 access
3. Note down: Access Key, Secret Key, Bucket name, Region

**Option B: Backblaze B2**
1. Create a B2 bucket
2. Create application key
3. Note down: Key ID, Application Key, Bucket name, Endpoint

**Option C: MinIO (Self-hosted)**
1. Deploy MinIO on a VPS or use MinIO's cloud service
2. Create access credentials
3. Note down: Endpoint, Access Key, Secret Key

### Step 2: Deploy Using Render Blueprint

1. **Fork/Clone the repository** to your GitHub account

2. **Update render.yaml** with your service names:
   ```yaml
   # Update the frontend URL in backend CORS
   - key: BACKEND_CORS_ORIGINS
     value: '["https://your-actual-frontend-url.onrender.com"]'
   
   # Update the API URL in frontend
   - key: NEXT_PUBLIC_API_URL
     value: https://your-actual-api-url.onrender.com
   ```

3. **Connect to Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository with render.yaml

4. **Configure Environment Variables** in Render Dashboard:

   **For Backend API & Celery Worker:**
   ```
   QDRANT_HOST=xyz-abc.us-east-1-0.aws.cloud.qdrant.io
   QDRANT_API_KEY=your-qdrant-api-key
   MINIO_ENDPOINT=s3.amazonaws.com  # or your S3-compatible endpoint
   MINIO_ACCESS_KEY=your-access-key
   MINIO_SECRET_KEY=your-secret-key
   MINIO_BUCKET_NAME=your-bucket-name
   MINIO_USE_SSL=true
   ```

### Step 3: Manual Deployment (Alternative)

If you prefer manual deployment:

#### 3.1 Create PostgreSQL Database
1. New → PostgreSQL
2. Name: `mediaindex-db`
3. Plan: Starter ($7/month)

#### 3.2 Create Redis Instance
1. New → Redis
2. Name: `mediaindex-redis`
3. Plan: Starter ($7/month)

#### 3.3 Deploy Backend API
1. New → Web Service
2. Connect GitHub repo
3. Settings:
   - Name: `mediaindex-api`
   - Root Directory: `backend`
   - Runtime: Docker
   - Plan: Starter ($7/month)
4. Add environment variables (see above)

#### 3.4 Deploy Celery Worker
1. New → Background Worker
2. Connect GitHub repo
3. Settings:
   - Name: `mediaindex-worker`
   - Root Directory: `backend`
   - Runtime: Docker
   - Docker Command: `celery -A core.celery_app worker --loglevel=info`
   - Plan: Starter ($7/month)
4. Add same environment variables as backend

#### 3.5 Deploy Frontend
1. New → Web Service
2. Connect GitHub repo
3. Settings:
   - Name: `mediaindex-frontend`
   - Root Directory: `frontend`
   - Runtime: Docker
   - Dockerfile Path: `./Dockerfile.production`
   - Plan: Starter ($7/month)
4. Environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://mediaindex-api.onrender.com
   ```

## 🔧 Post-Deployment Configuration

### 1. Update CORS Settings
Once your frontend is deployed, update the backend's CORS settings:
```
BACKEND_CORS_ORIGINS=["https://mediaindex-frontend.onrender.com"]
```

### 2. Initialize Database
The database tables will be created automatically on first startup.

### 3. Create First User
Use the API documentation at `https://your-api-url.onrender.com/docs` to:
1. Register a new user via `/api/v1/auth/register`
2. Login to get JWT token

### 4. Test Upload
1. Login to your frontend
2. Upload a test image
3. Check logs to ensure AI processing works

## 💰 Cost Breakdown (Render Starter Plan)

- PostgreSQL: $7/month
- Redis: $7/month
- Backend API: $7/month
- Celery Worker: $7/month
- Frontend: $7/month
- **Total: $35/month**

External services:
- Qdrant Cloud: Free tier (up to 1GB)
- S3 Storage: Pay per usage

## 🚀 Performance Optimization

### 1. Scaling Workers
For heavy load, scale Celery workers:
```yaml
# In render.yaml, add more workers
- type: worker
  name: mediaindex-worker-2
  # ... same config
```

### 2. Caching
Implement Redis caching for:
- Search results
- Processed media metadata
- User sessions

### 3. CDN for Media
Use Cloudflare or Render's CDN for serving media files.

## 🔍 Monitoring

1. **Render Dashboard**: Monitor service health, logs, metrics
2. **Sentry**: Add error tracking (optional)
3. **Custom Metrics**: Implement Prometheus metrics

## 🆘 Troubleshooting

### Common Issues:

1. **"Connection refused" to Qdrant**
   - Check QDRANT_HOST format (no https://)
   - Verify API key is set

2. **S3 upload failures**
   - Check bucket permissions
   - Verify endpoint URL format
   - Ensure SSL setting matches provider

3. **Celery tasks not processing**
   - Check Redis connection
   - Verify worker is running
   - Check logs for errors

4. **CORS errors**
   - Update BACKEND_CORS_ORIGINS with exact frontend URL
   - Include protocol (https://)

### Debug Commands:
```bash
# Check service logs in Render dashboard
# Or use Render CLI:
render logs mediaindex-api --tail

# SSH into service (if enabled):
render ssh mediaindex-api
```

## 🔐 Security Checklist

- [ ] Change default JWT_SECRET
- [ ] Use strong passwords
- [ ] Enable Render's DDoS protection
- [ ] Set up proper S3 bucket policies
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS (automatic on Render)
- [ ] Regular backups of PostgreSQL

## 📈 Next Steps

1. **Custom Domain**: Add your domain in Render settings
2. **Auto-scaling**: Configure based on CPU/memory usage
3. **Monitoring**: Set up alerts for service health
4. **Backups**: Enable automatic PostgreSQL backups
5. **CI/CD**: Set up GitHub Actions for automated testing

## 📚 Resources

- [Render Documentation](https://render.com/docs)
- [Qdrant Cloud Docs](https://qdrant.tech/documentation/cloud/)
- [PostgreSQL on Render](https://render.com/docs/databases)
- [Docker on Render](https://render.com/docs/docker) 