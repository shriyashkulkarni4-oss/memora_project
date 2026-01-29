# Memora - Smart Bookmark & Link Manager

A modern bookmark and link management application with AI-powered organization capabilities. Save screenshots, hyperlinks from news articles, LinkedIn posts, Twitter, and more.

## Quick Start with Docker

```bash
# Clone and start all services
docker-compose up -d

# Services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/api/docs
# - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
# - PostgreSQL: localhost:5432
```

## Tech Stack

### Frontend (Web) - `apps/web`
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Routing**: React Router v6
- **Icons**: Lucide React

### Backend - `apps/api`
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy (async)
- **File Storage**: MinIO S3-compatible
- **Auth**: JWT with python-jose
- **Migrations**: Alembic

### Mobile (Planned)
- **Framework**: React Native
- **Navigation**: React Navigation
- **State**: Shared Zustand store

## Project Structure

```
memora/
├── apps/
│   ├── web/                    # React Frontend
│   │   ├── src/
│   │   │   ├── components/     # UI Components
│   │   │   ├── hooks/          # Custom hooks (useAuth)
│   │   │   ├── services/       # API client
│   │   │   ├── store/          # Zustand state
│   │   │   └── types/          # TypeScript interfaces
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   └── api/                    # FastAPI Backend
│       ├── app/
│       │   ├── api/            # API routes
│       │   ├── models/         # SQLAlchemy models
│       │   └── services/       # Business logic (storage)
│       ├── alembic/            # Database migrations
│       ├── Dockerfile
│       └── requirements.txt
│
├── docker-compose.yml          # All services orchestration
├── .env.example                # Environment template
└── README.md
```

## Features

- **Dashboard**: Overview with stats, recent links, and quick actions
- **Link Management**: Save URLs and screenshots with metadata
- **Screenshot Upload**: Capture and store visual bookmarks via MinIO
- **Categories**: Organize links with custom colors and icons
- **Tags**: Flexible tagging system
- **Favorites**: Quick access to starred links
- **Archive**: Keep old links without clutter
- **Search**: Full-text search across all fields
- **Authentication**: Secure JWT-based user accounts
- **AI Ready**: Architecture prepared for n8n pipeline integration

## Development Setup

### Option 1: Docker (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec api alembic upgrade head

# Stop services
docker-compose down
```

### Option 2: Local Development

#### Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Start dev server
npm run dev

# Open http://localhost:3000
```

#### Backend

```bash
cd apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API docs at http://localhost:8000/api/docs
```

#### Database & Storage (Docker)

```bash
# Start only PostgreSQL and MinIO
docker-compose up -d postgres minio
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login, get JWT token |
| GET | /api/auth/me | Get current user info |

### Links
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/links | List links (with filters) |
| POST | /api/links | Create new link |
| POST | /api/links/screenshot | Upload screenshot link |
| GET | /api/links/:id | Get single link |
| PATCH | /api/links/:id | Update link |
| DELETE | /api/links/:id | Delete link |
| POST | /api/links/:id/favorite | Toggle favorite |
| POST | /api/links/:id/archive | Toggle archive |

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/categories | List categories |
| POST | /api/categories | Create category |
| PATCH | /api/categories/:id | Update category |
| DELETE | /api/categories/:id | Delete category |

### Tags
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/tags | List tags |
| POST | /api/tags | Create tag |
| DELETE | /api/tags/:id | Delete tag |

## Environment Variables

### Docker (.env)
```env
# PostgreSQL
POSTGRES_USER=memora
POSTGRES_PASSWORD=memora123
POSTGRES_DB=memora

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Backend
SECRET_KEY=your-super-secret-key-change-in-production
```

### Frontend (apps/web/.env)
```env
VITE_API_URL=http://localhost:8000
```

### Backend (apps/api/.env)
```env
DATABASE_URL=postgresql+asyncpg://memora:memora123@localhost:5432/memora
SECRET_KEY=your-secret-key
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=memora-uploads
MINIO_SECURE=false
```

## React Native Migration Guide

The codebase is structured for easy React Native migration:

1. **Shared Types**: `apps/web/src/types/index.ts` - use directly
2. **Shared Store**: `apps/web/src/store/linkStore.ts` - works with React Native
3. **API Client**: `apps/web/src/services/api.ts` - portable with minor adjustments

### Component Mapping
- `<Link>` → `<TouchableOpacity>` + navigation
- Tailwind classes → StyleSheet or NativeWind
- `lucide-react` → `lucide-react-native`

## AI Integration (n8n Pipeline)

The app is designed for AI processing via n8n workflows:

1. **Link Metadata Extraction**: Fetch OG tags, favicon, title
2. **Screenshot OCR**: Process images with Ollama/Tesseract
3. **Content Summarization**: Generate AI summaries
4. **Auto-categorization**: Suggest categories and tags

### Webhook Payload
```json
{
  "link_id": "uuid",
  "url": "https://example.com",
  "type": "url|screenshot",
  "user_id": "uuid"
}
```

## Production Deployment

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Frontend (Vercel/Netlify)
```bash
cd apps/web
npm run build
# Deploy dist/ folder
```

### Backend (Docker)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## License

MIT
