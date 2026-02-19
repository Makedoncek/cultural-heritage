# CultureMap Ukraine

A web platform for mapping Ukrainian cultural heritage sites. Registered users can submit objects (castles, churches, monuments, etc.), which are reviewed by administrators before appearing on the map.

## Features

- Interactive map of Ukraine with clustered markers (Leaflet.js)
- Filter objects by category tags
- Submit and manage your own cultural objects
- Three-tier moderation workflow: `pending → approved → archived`
- JWT authentication with role-based access (Guest / User / Admin)
- Admin panel for moderation and tag management

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Frontend | React 18 + TypeScript + Vite 5 + Leaflet.js |
| Backend | Django 5 + Django REST Framework + SimpleJWT |
| Database | PostgreSQL 15 (Docker) |
| Auth | JWT (access + refresh tokens) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

## Getting Started

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

Create a `.env` file in `backend/`:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=cultural_heritage
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

```bash
python manage.py migrate
python manage.py createsuperuser
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

## Development Commands

### Backend

```bash
python manage.py runserver       # Start dev server
python manage.py test            # Run tests
python manage.py makemigrations  # Create migrations
python manage.py migrate         # Apply migrations
python manage.py seed_data       # Load sample data
```

### Frontend

```bash
npm run dev    # Start dev server
npm run build  # Production build
npx tsc --noEmit  # Type check
```

## Project Structure

```
cultural-heritage/
├── backend/
│   ├── config/          # Django settings and URLs
│   ├── objects/         # Main app: models, views, serializers
│   └── manage.py
├── frontend/            # React SPA (in progress)
├── docker-compose.yml   # PostgreSQL service
└── docs/                # Project documentation
```

## Access

| URL | Description |
| :--- | :--- |
| `http://localhost:8000/admin/` | Django admin panel |
| `http://localhost:8000/api/` | REST API |
| `http://localhost:5173/` | React frontend (dev) |
