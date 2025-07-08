# AI-Powered Media Indexing & Search Platform

A scalable system that automatically ingests, classifies, tags, and enables semantic search across a custom library of image and video footage using state-of-the-art AI models and vector databases.

## 🚀 Features

- **AI-Powered Processing**: Automatic image/video analysis using CLIP and BLIP models
- **Semantic Search**: Natural language search across your media library
- **Smart Tagging**: AI-generated captions and tags for all media
- **Vector Search**: Fast similarity search using Qdrant vector database
- **Scalable Storage**: MinIO/S3-compatible object storage
- **Modern UI**: Beautiful React/Next.js interface with Tailwind CSS
- **Authentication**: Secure JWT-based authentication
- **Background Processing**: Celery workers for async media processing

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL + SQLAlchemy
- **Vector DB**: Qdrant
- **Storage**: MinIO (S3-compatible)
- **Cache/Queue**: Redis
- **AI Models**: CLIP, BLIP-2
- **Task Queue**: Celery

### Frontend
- **Framework**: Next.js 14
- **UI**: Tailwind CSS
- **State**: Zustand
- **API Client**: Axios + React Query

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- 8GB+ RAM recommended
- GPU optional (for faster AI processing)

## 🚀 Quick Start

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd VIDEO-MONTEIZATION
```

2. **Set up environment variables**
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your settings
```

3. **Start the services**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## 🔧 Development Setup

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
VIDEO-MONTEIZATION/
├── backend/
│   ├── api/          # API endpoints
│   ├── core/         # Core configuration
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── main.py       # FastAPI app
├── frontend/
│   ├── app/          # Next.js app directory
│   ├── components/   # React components
│   ├── services/     # API services
│   └── stores/       # Zustand stores
├── docker-compose.yml
└── README.md
```

## 🔑 Default Credentials

- **MinIO**: minioadmin / minioadmin
- **PostgreSQL**: mediaindex / mediaindex123

⚠️ **Important**: Change these in production!

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/token` - Login
- `GET /api/v1/auth/me` - Get current user

### Media Upload
- `POST /api/v1/upload/single` - Upload single file
- `POST /api/v1/upload/bulk` - Upload multiple files
- `GET /api/v1/upload/status/{id}` - Check processing status

### Search
- `POST /api/v1/search/semantic` - Natural language search
- `GET /api/v1/search/keyword` - Keyword search
- `GET /api/v1/search/tags` - Get popular tags

### Media Management
- `GET /api/v1/media` - List media
- `GET /api/v1/media/{id}` - Get media details
- `PUT /api/v1/media/{id}` - Update media
- `DELETE /api/v1/media/{id}` - Delete media

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

## 🚀 Production Deployment

1. Update environment variables for production
2. Use proper SSL certificates
3. Set up proper backup strategies
4. Configure monitoring (Prometheus/Grafana)
5. Use Kubernetes or Docker Swarm for orchestration

## 📈 Scaling Considerations

- **Horizontal Scaling**: Add more Celery workers
- **GPU Support**: Use NVIDIA Docker for GPU acceleration
- **CDN**: Use CloudFlare for global media delivery
- **Database**: Consider read replicas for PostgreSQL
- **Caching**: Implement Redis caching for frequent queries

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions, please create a GitHub issue. 