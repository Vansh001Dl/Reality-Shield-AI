# RealityShield-AI: Road Safety Monitoring & AI-Powered Route Recommendation Platform

[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-blue)]()
[![Python Version](https://img.shields.io/badge/python-3.11-blue)]()
[![Node.js Version](https://img.shields.io/badge/node-18+-green)]()

## Overview

RealityShield-AI is a comprehensive road safety monitoring and AI-powered route recommendation platform that combines computer vision, machine learning, and natural language processing to provide real-time safety assessments and route recommendations.

### Key Features

- **Computer Vision**: YOLO-based object detection (cars, trucks, buses, bikes, pedestrians, potholes)
- **Risk Assessment**: Machine learning-powered risk scoring with SHAP explainability
- **Route Recommendations**: AI-optimized safest route calculation
- **Conversational AI**: Context-aware safety assistant with natural language interface
- **Real-time Dashboard**: Interactive visualization of road safety metrics
- **Video Analysis**: Upload and analyze recorded road footage
- **User Authentication**: JWT-based secure user authentication
- **Database Integration**: PostgreSQL with PostGIS for spatial data
- **Cloud Ready**: Dockerized with S3 integration for video storage

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RealityShield-AI                          │
├─────────────────────────────┬───────────────────────────────────┤
│      Frontend (React)       │         Backend (FastAPI)         │
├─────────────────────────────┼───────────────────────────────────┤
│  Dashboard                  │  • Detection Service              │
│  Route Recommendation       │  • Risk Assessment Service        │
│  Safety Chat (LLM)          │  • Explanation Service (SHAP)     │
│  Analytics                  │  • Video Processing Service         │
│  Video Uploader             │  • Authentication Service         │
└─────────────────────────────┴───────────────────────────────────┘
                      │                      │
                      ▼                      ▼
     ┌──────────────────────────────────────────────┐
     │          Database (PostgreSQL + PostGIS)     │
     │  • Detections                                  │
     │  • Risk Scores                                 │
     │  • Route History                               │
     │  • Alerts                                      │
     └──────────────────────────────────────────────┘
                      │
                      ▼
     ┌──────────────────────────────────────────────┐
     │         Cloud Storage (S3) for Videos        │
     └──────────────────────────────────────────────┘
```

## Backend development

From `backend/`, install dependencies with `python -m pip install -r requirements.txt`.
Database schema changes use Alembic: `alembic upgrade head` applies migrations and
`alembic revision --autogenerate -m "describe change"` creates a migration draft.
Run backend tests with `python -m pytest --cov=app --cov-report=term-missing`.

All application routes are available under `/api/v1/...`; the previous `/api/...`
routes remain temporarily available for existing clients. Prometheus metrics are
served at `/metrics` and `/api/v1/metrics`. Live analysis progress is sent over
`/api/v1/ws/alerts`. The per-process sliding-window rate limit uses `RATE_LIMIT`
and `RATE_LIMIT_WINDOW`.

Video jobs run in the local worker by default. To use Celery, configure Redis with
`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, set `CELERY_ENABLED=true`, and run
`celery -A app.core.celery_app.celery_app worker --loglevel=info` from `backend/`.

## Project Structure

```
RealityShield-AI/
├── backend/
│   ├── app/
│   │   ├── api/                 # API route definitions
│   │   ├── core/                # Core configuration and utilities
│   │   ├── db/                  # Database configuration
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic services
│   │   ├── utils/               # Utility functions
│   │   └── main.py              # FastAPI application entry point
│   ├── ml_models/               # Trained ML models
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile              # Backend container
├── frontend/
│   ├── src/
│   │   ├── pages/               # Page components
│   │   ├── components/          # Reusable components
│   │   ├── services/            # API services
│   │   ├── styles/              # CSS styles
│   │   └── App.jsx              # Main application
│   ├── package.json             # Node.js dependencies
│   └── Dockerfile              # Frontend container
├── database/
│   ├── schema.sql              # Database schema
│   └── seed_data.sql           # Seed data
├── scripts/
│   └── init_database.py        # Database initialization script
├── docs/
│   ├── architecture_diagram.png
│   └── frontend_reference.png
├── docker-compose.yml          # Docker orchestration
├── start.bat                   # Windows startup script
├── start.ps1                   # PowerShell startup script
└── .env.example                # Environment configuration template
```

## Quick Start

### Option 1: One-Click Start (Windows)

```powershell
# From the RealityShield-AI directory
.\start.ps1
```

### Option 2: Manual Setup

#### Backend Setup

```powershell
# Navigate to backend
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../.env.example ../.env
# Edit .env with your configuration

# Start the server
$env:APP_ENV = "development"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

For Bash or another Unix-like shell, activate the environment with
`source .venv/bin/activate` instead.

#### Frontend Setup

Open a separate terminal from the `RealityShield-AI` directory. The frontend's
`package.json` is inside `frontend`, so run npm commands from that directory:

```powershell
cd .\frontend
# Install dependencies
npm install

# Create environment file
"VITE_API_BASE_URL=http://localhost:8001" | Set-Content .env.local
"VITE_API_KEY=your_api_key_here" | Add-Content .env.local

# Start development server
npm run dev -- --host 0.0.0.0 --port 5173
```
.\.venv\Scripts\A

### Option 3: Docker

```bash
# Start all services
docker-compose up --build

# Access services:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Database: postgresql://localhost:5432
```

## API Documentation

Once the backend is running, visit:

- **Swagger UI**: http://localhost:8001/api/docs
- **ReDoc**: http://localhost:8001/api/redoc

### Authentication

#### Login

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "user_123"
}
```

#### Protected Endpoints

Include token in Authorization header:
```
Authorization: Bearer <access_token>
```

### Video Upload

```bash
POST /api/detection/video
Content-Type: multipart/form-data
X-API-Key: your_api_key
Authorization: Bearer <access_token>

File: video.mp4
```

### Risk Assessment

```bash
POST /api/risk/score
Content-Type: application/json

{
  "camera_id": "cam_01",
  "traffic_density": 0.5,
  "pedestrian_count": 5,
  "vehicle_count": 15,
  "pothole_count": 2,
  "speed_kmh": 50,
  "weather_risk": 0.3,
  "road_quality": 0.7,
  "night_mode": false
}
```

## Environment Configuration

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string; PostgreSQL for production | SQLite at `backend/data/users.sqlite3` in development |
| `SECRET_KEY` | JWT secret key | Random generated |
| `API_KEY` | API authentication key | Random generated |
| `GROQ_API_KEY` | Groq API key for chat | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `S3_BUCKET_NAME` | AWS S3 bucket for video storage | `realityshield-videos` |
| `S3_DATASET_STORAGE_PREFIX` | S3 prefix for source videos and complete analysis datasets | `datasets` |
| `AWS_ACCESS_KEY_ID` | AWS access key | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - |
| `AWS_SESSION_TOKEN` | Temporary AWS session token, when required | - |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000,http://localhost:5173` |
| `MAX_FILE_SIZE_MB` | Maximum video upload size | `100` |

On each successful video analysis, the backend stores the source video and its
complete detections/metadata in S3 when the archive is reachable. In development,
an unavailable S3 archive falls back to `backend/data/video_datasets` so local
analysis can still complete. Production requires S3. The dashboard restores the
latest saved analysis when available and lets you select older videos from the
**Saved videos** list. Configure the bucket, region, and AWS credentials in the
root `.env`, or use an AWS IAM role for credentials. The AWS identity needs
`s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions for the bucket
and dataset prefix. Include `s3:DeleteObject` to allow cleanup if a dataset
manifest cannot be saved.

## Database Schema

```sql
-- Detections table
CREATE TABLE detections (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    source_name VARCHAR(255),
    detected_at TIMESTAMPTZ,
    total_detections INTEGER,
    objects JSONB,
    location GEOGRAPHY(POINT, 4326)
);

-- Risk scores table
CREATE TABLE risk_scores (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    calculated_at TIMESTAMPTZ,
    score NUMERIC(4,3),
    severity VARCHAR(20),
    confidence NUMERIC(4,3),
    factors JSONB,
    recommendations JSONB
);

-- Video analysis history
CREATE TABLE video_analysis_history (
    id BIGSERIAL PRIMARY KEY,
    analyzed_at TIMESTAMPTZ,
    source_name VARCHAR(255),
    risk_score NUMERIC(4,3),
    severity VARCHAR(20),
    -- ... additional fields
);
```

## Development

### Project Goals

1. **MVP**: Basic video upload and detection ✓
2. **Risk Assessment**: Risk scoring with ML model ✓
3. **Route Optimization**: Route recommendations ✓
4. **Natural Language**: Safety chat assistant ✓
5. **Explainability**: SHAP-based risk explanations ✓
6. **Analytics Dashboard**: Comprehensive analytics ✓
7. **User Management**: Authentication and roles ✓
8. **Cloud Deployment**: Production-ready infrastructure ✓

### Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

### Linting

```bash
# Backend
cd backend
black .
isort .

# Frontend
cd frontend
npm run lint
```

## Production Deployment

### Environment Setup

```bash
# Production environment variables
export APP_ENV=production
export DATABASE_URL=postgresql://user:password@db:5432/realityshield
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export GROQ_API_KEY=your_production_key
export GEMINI_API_KEY=your_production_key
```

### Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.9'
services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - APP_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### Kubernetes Deployment

```yaml
# k8s/realityshield-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: realityshield-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: realityshield
  template:
    metadata:
      labels:
        app: realityshield
    spec:
      containers:
      - name: backend
        image: realityshield/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: realityshield-secrets
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - For the excellent web framework
- [YOLO](https://ultralytics.com/) - For object detection
- [Leaflet](https://leafletjs.com/) - For interactive maps
- [Recharts](https://recharts.org/) - For data visualization

## Support

For issues, questions, or contributions, please contact the development team or open an issue on GitHub.
