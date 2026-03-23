# CultureMap Ukraine

A web platform for mapping Ukrainian cultural heritage sites. Registered users can submit objects (castles, churches, monuments, etc.), which are reviewed by administrators before appearing on the map.

## Live Demo

| | URL |
| :--- | :--- |
| Frontend | [cultural-heritage.vercel.app](https://cultural-heritage.vercel.app) |
| Backend API | [cultural-heritage-production.up.railway.app/api/](https://cultural-heritage-production.up.railway.app/api/) |

## Features

- Interactive map of Ukraine with clustered markers (Leaflet.js)
- Filter objects by category tags
- Search by title with debounced dropdown results
- Submit and manage your own cultural objects (add, edit, archive)
- Location picker with fullscreen mode and geolocation
- Three-tier moderation workflow: `pending → approved → archived`
- Visual distinction for pending objects (grey markers)
- JWT authentication with role-based access (Guest / User / Admin)
- Admin panel for moderation and tag management
- Coordinate validation against Ukraine border polygon (Shapely)

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Frontend | React 19 + TypeScript + Vite 7 + Tailwind CSS v4 + Leaflet.js (react-leaflet v5) |
| Backend | Django 5 + Django REST Framework + SimpleJWT |
| Database | PostgreSQL 15 (Docker) |
| Auth | JWT (access + refresh tokens) |
| Deployment | Vercel (frontend) + Railway (backend) + Docker (self-hosted) |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Browser                        │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐         ┌──────────────┐
│   Vercel     │         │  nginx :80   │
│  (frontend)  │         │  (Docker)    │
└──────┬───────┘         └──────┬───────┘
       │                   ┌────┴────┐
       │                   ▼         ▼
       │              /api/*    /* (SPA)
       │                   │
       ▼                   ▼
┌──────────────────────────────┐
│  Django + DRF + Gunicorn     │
│  (Railway or Docker :8000)   │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  PostgreSQL 15               │
│  (Railway or Docker :5432)   │
└──────────────────────────────┘
```

## API Endpoints

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| POST | `/api/auth/register/` | Register new user | No |
| POST | `/api/auth/login/` | Login (JWT tokens) | No |
| POST | `/api/auth/refresh/` | Refresh access token | No |
| GET | `/api/tags/` | List all tags | No |
| GET | `/api/objects/` | List objects (with filtering, search) | No |
| GET | `/api/objects/{id}/` | Object detail | No |
| POST | `/api/objects/` | Create object | Yes |
| PUT/PATCH | `/api/objects/{id}/` | Update object | Author/Admin |
| DELETE | `/api/objects/{id}/` | Archive object (soft delete) | Author/Admin |
| GET | `/api/objects/my/` | Current user's objects | Yes |
| GET | `/api/health/` | Health check | No |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

## Getting Started (Development)

### 1. Clone the repository

```bash
git clone <repo-url>
cd cultural-heritage
```

### 2. Start the database

```bash
docker-compose up -d
```

### 3. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/` (see `.env.example` in project root):

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=culturemap
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

```bash
python manage.py migrate
python manage.py seed_data       # Creates admin, test user, tags, 50 objects
python manage.py runserver
```

### 4. Set up the frontend

```bash
cd frontend
npm install
```

Create a `.env` file in `frontend/`:

```env
VITE_API_URL=http://localhost:8000/api
```

```bash
npm run dev
```

## Production Deployment (Docker)

Deploy the full stack with a single command:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This starts:
- **PostgreSQL** — database with health checks
- **Backend** — Django + Gunicorn, auto-migrates on startup
- **Frontend** — React SPA served by nginx reverse proxy

The app is available at `http://localhost`.

To seed data:
```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_data
```

## Development Commands

### Backend

```bash
python manage.py runserver       # Start dev server
python manage.py test            # Run testspython manage.py makemigrations  # Create migrations
python manage.py migrate         # Apply migrations
python manage.py seed_data       # Load sample data (admin/admin123, testuser/testpass123)
```

### Frontend

```bash
npm run dev        # Start dev server
npm run build      # Production build
npx tsc --noEmit   # Type check
```

## Project Structure

```
cultural-heritage/
├── backend/
│   ├── config/              # Django settings and URLs
│   ├── objects/             # Main app: models, views, serializers
│   │   ├── data/            # Ukraine border GeoJSON
│   │   ├── management/      # seed_data command
│   │   └── tests/           # Test suite│   ├── Dockerfile           # Production image (python:3.14-slim + gunicorn)
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/      # Map, Layout, Objects, RequireAuth
│   │   ├── pages/           # Home, Login, Register, Add/Edit/Detail/MyObjects
│   │   ├── services/        # API client, auth/objects/tags services
│   │   ├── context/         # AuthContext (JWT)
│   │   └── types/           # TypeScript interfaces
│   ├── Dockerfile           # Multi-stage build (node:20-alpine → nginx:alpine)
│   └── package.json
├── nginx/
│   └── nginx.conf           # Reverse proxy config for Docker
├── docker-compose.yml        # Development (PostgreSQL only)
├── docker-compose.prod.yml   # Production (db + backend + frontend)
└── .env.example              # Environment variables template
```

## Test Accounts (seed_data)

| Role | Username | Password |
| :--- | :--- | :--- |
| Admin | `admin` | `admin123` |
| User | `testuser` | `testpass123` |
