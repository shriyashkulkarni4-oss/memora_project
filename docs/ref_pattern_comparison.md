# Pattern Comparison: cml-memora vs cml-prompts-hive

**Date:** 2026-01-30
**Purpose:** Document structural differences and migration requirements

---

## Directory Structure Comparison

### Current cml-memora Structure
```
cml-memora/
├── apps/
│   ├── api/                    # Backend
│   │   ├── alembic/           # Migrations
│   │   ├── app/
│   │   │   ├── api/           # Routes (no versioning)
│   │   │   ├── models/        # SQLAlchemy models
│   │   │   └── services/      # Storage service
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── web/                    # Frontend
│       ├── src/
│       │   ├── components/    # All components flat
│       │   ├── hooks/
│       │   ├── services/
│       │   ├── store/
│       │   └── types/
│       ├── Dockerfile
│       └── package.json
│
├── docs/
├── docker-compose.yml
└── .env.example
```

### Target cml-prompts-hive Structure
```
cml-memora/
├── backend/                    # NOT apps/api
│   ├── app/
│   │   ├── api/v1/            # Versioned routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── links.py
│   │   │   ├── categories.py
│   │   │   ├── tags.py
│   │   │   └── router.py      # Main v1 router
│   │   ├── core/              # Core utilities
│   │   │   ├── deps.py        # Dependencies
│   │   │   ├── security.py    # JWT, passwords
│   │   │   ├── encryption.py  # Encryption utils
│   │   │   └── redis.py       # Redis client (if using)
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas (NEW)
│   │   ├── services/          # Business logic
│   │   ├── middleware/        # Error handling, etc.
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings
│   │   └── database.py        # DB connection
│   ├── migrations/            # NOT alembic/
│   │   ├── env.py
│   │   ├── versions/
│   │   └── script.py.mako
│   ├── tests/                 # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_*.py
│   ├── scripts/               # Utility scripts
│   │   ├── __init__.py
│   │   └── seed_db.py
│   ├── pyproject.toml         # Modern Python config
│   ├── requirements.txt
│   ├── run.py                 # Entry point
│   ├── alembic.ini
│   └── Dockerfile
│
├── frontend/                   # NOT apps/web
│   ├── src/
│   │   ├── pages/             # Route components (NEW)
│   │   │   ├── Landing.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Links.tsx
│   │   │   ├── Favorites.tsx
│   │   │   ├── Archive.tsx
│   │   │   ├── Categories.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/        # Organized components
│   │   │   ├── layout/        # Layout components
│   │   │   │   └── Layout.tsx
│   │   │   ├── ui/            # Reusable UI components
│   │   │   │   ├── FormField.tsx
│   │   │   │   └── index.ts
│   │   │   ├── links/         # Link-specific components
│   │   │   │   ├── LinkCard.tsx
│   │   │   │   ├── LinkList.tsx
│   │   │   │   └── LinkForm.tsx
│   │   │   └── categories/    # Category components
│   │   │       └── CategoryForm.tsx
│   │   ├── hooks/
│   │   │   ├── index.ts       # Export barrel
│   │   │   ├── useAuth.tsx
│   │   │   └── useDebounce.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── store/
│   │   │   └── linkStore.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
│
├── .agent/                     # AI agent documentation
│   └── prompts/
│       ├── README.md
│       ├── PRD.md
│       └── tasks-*.md
│
├── docs/                       # Project documentation
│   ├── MEMORA_REQUIREMENTS.md
│   ├── PROJECT_STATUS.md
│   ├── PATTERN_COMPARISON.md
│   └── MIGRATION_TASK_TRACKER.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Key Differences

### 1. Top-Level Structure

| Aspect | cml-memora (Current) | cml-prompts-hive (Target) |
|--------|---------------------|---------------------------|
| Backend directory | `apps/api/` | `backend/` |
| Frontend directory | `apps/web/` | `frontend/` |
| Monorepo style | `apps/*` pattern | Direct `backend/frontend/` |
| Agent docs | N/A | `.agent/prompts/` |

**Migration Required:** Rename directories, update all import paths

---

### 2. Backend API Structure

| Aspect | Current | Target |
|--------|---------|--------|
| API versioning | No versioning (`app/api/`) | Versioned (`app/api/v1/`) |
| Route organization | Direct routes | Router with versioning |
| Core utilities | Scattered | Organized in `app/core/` |
| Schemas | Mixed with routes | Separate `app/schemas/` |
| Business logic | In routes | Separate `app/services/` |
| Tests | Missing | `tests/` directory |
| Scripts | Missing | `scripts/` directory |
| Dependencies | `requirements.txt` | `pyproject.toml` + `requirements.txt` |

**Key Files to Add:**
- `app/api/v1/router.py` - Main router aggregator
- `app/core/deps.py` - Dependency injection
- `app/core/security.py` - JWT and auth utilities
- `app/schemas/*.py` - Pydantic request/response models
- `app/config.py` - Centralized settings
- `run.py` - Application entry point
- `pyproject.toml` - Modern Python configuration

---

### 3. Frontend Structure

| Aspect | Current | Target |
|--------|---------|--------|
| Component organization | Flat structure | Organized by type and feature |
| Route components | Mixed with components | Separate `pages/` directory |
| Layouts | In components | `components/layout/` |
| UI components | Scattered | `components/ui/` |
| Feature components | N/A | `components/links/`, etc. |
| Hooks | Single file | Barrel exports with `index.ts` |
| Pages | Components as pages | Dedicated `pages/` directory |

**Key Reorganizations:**
- Move route components to `src/pages/`
- Create `components/layout/` for Layout
- Create `components/ui/` for reusable UI
- Create `components/links/` for link-specific components
- Add `hooks/index.ts` barrel export
- Update App.tsx to import from pages/

---

### 4. Docker & Services

| Aspect | Current | Target |
|--------|---------|--------|
| Services | PostgreSQL, MinIO, API, Web | PostgreSQL, Redis, Backend, Frontend |
| Service naming | `api`, `web` | `backend`, `frontend` |
| Container names | `memora-*` | `memora-*` |
| Health checks | Basic | Comprehensive |
| Volume mounting | Basic | Hot reload optimized |
| Redis | Not present | Present for caching |

**Changes Required:**
- Rename `api` service to `backend`
- Rename `web` service to `frontend`
- Add Redis service (for future caching, rate limiting)
- Update health checks
- Update environment variables

---

### 5. Configuration & Settings

| Aspect | Current | Target |
|--------|---------|--------|
| Backend config | Environment variables | `app/config.py` with settings class |
| CORS | Basic | Configured via settings |
| Lifespan events | Missing | Proper startup/shutdown handlers |
| Logging | Basic | Structured logging |

---

### 6. Missing Components in cml-memora

Components present in prompts-hive but missing in memora:

#### Backend:
- [ ] `app/config.py` - Centralized settings management
- [ ] `app/core/deps.py` - Dependency injection
- [ ] `app/core/security.py` - JWT utilities, password hashing
- [ ] `app/core/encryption.py` - Data encryption (for sensitive data)
- [ ] `app/core/redis.py` - Redis client (if using caching)
- [ ] `app/schemas/` - Separate Pydantic schemas
- [ ] `app/middleware/` - Error handling, logging
- [ ] `tests/` - Test suite
- [ ] `scripts/` - Database seeding, utilities
- [ ] `run.py` - Application entry point
- [ ] `pyproject.toml` - Modern Python configuration

#### Frontend:
- [ ] `pages/` - Dedicated page components
- [ ] `components/layout/` - Layout components
- [ ] `components/ui/` - Reusable UI components
- [ ] Feature-based component organization
- [ ] Barrel exports (`index.ts`)

#### Root:
- [ ] `.agent/prompts/` - AI agent documentation
- [ ] Redis service in docker-compose

---

## Migration Strategy

### Phase 1: Backend Restructure (High Priority)

1. **Rename directories**
   - `apps/api/` → `backend/`
   - `apps/` → (remove after migration)

2. **Add missing directories**
   - `backend/app/core/`
   - `backend/app/schemas/`
   - `backend/app/middleware/`
   - `backend/tests/`
   - `backend/scripts/`

3. **Create core files**
   - `backend/app/config.py`
   - `backend/app/core/deps.py`
   - `backend/app/core/security.py`
   - `backend/run.py`
   - `backend/pyproject.toml`

4. **Reorganize API**
   - Create `app/api/v1/` directory
   - Move routes to `v1/` with proper naming
   - Create `app/api/v1/router.py`
   - Update `main.py` to use v1 router

5. **Extract schemas**
   - Move Pydantic models from routes to `app/schemas/`
   - Create separate schema files

6. **Refactor services**
   - Enhance existing services
   - Extract business logic from routes

7. **Update migrations**
   - Move `alembic/` to `migrations/`
   - Update alembic.ini path references

---

### Phase 2: Frontend Restructure (High Priority)

1. **Rename directories**
   - `apps/web/` → `frontend/`

2. **Create pages directory**
   - Create `src/pages/`
   - Move route components to pages

3. **Reorganize components**
   - Create `src/components/layout/`
   - Create `src/components/ui/`
   - Create `src/components/links/`
   - Create `src/components/categories/`
   - Move components to appropriate directories

4. **Add barrel exports**
   - Create `src/hooks/index.ts`
   - Create `src/components/ui/index.ts`

5. **Update imports**
   - Update all import paths throughout the app

---

### Phase 3: Docker & Infrastructure (Medium Priority)

1. **Update docker-compose.yml**
   - Rename services (`api` → `backend`, `web` → `frontend`)
   - Add Redis service
   - Update container names
   - Add health checks
   - Update volume mounts

2. **Update .env.example**
   - Add new environment variables
   - Match prompts-hive structure

3. **Update Dockerfiles**
   - Optimize build process
   - Update paths

---

### Phase 4: Documentation & Tooling (Lower Priority)

1. **Create .agent directory**
   - Add `.agent/prompts/`
   - Document AI agent prompts
   - Add phase tasks

2. **Add testing infrastructure**
   - Backend: pytest setup
   - Frontend: Vitest/Jest setup

3. **Add scripts**
   - Database seeding
   - Development helpers

---

## File Mapping Reference

### Files to Rename/Move

| Current Path | Target Path | Action |
|-------------|-------------|--------|
| `apps/api/` | `backend/` | Rename directory |
| `apps/web/` | `frontend/` | Rename directory |
| `apps/api/alembic/` | `backend/migrations/` | Rename directory |
| `apps/api/app/api/` | `backend/app/api/v1/` | Move + version |
| `apps/web/src/components/Dashboard.tsx` | `frontend/src/pages/Dashboard.tsx` | Move to pages |
| `apps/web/src/components/Login.tsx` | `frontend/src/pages/Login.tsx` | Move to pages |
| `apps/web/src/components/Register.tsx` | `frontend/src/pages/Register.tsx` | Move to pages |
| `apps/web/src/components/LinkList.tsx` | `frontend/src/pages/Links.tsx` | Move + rename |
| `apps/web/src/components/Layout.tsx` | `frontend/src/components/layout/Layout.tsx` | Move to layout |
| `apps/web/src/components/LinkCard.tsx` | `frontend/src/components/links/LinkCard.tsx` | Move to links |
| `apps/web/src/components/LinkForm.tsx` | `frontend/src/components/links/LinkForm.tsx` | Move to links |

### Files to Create

**Backend:**
- `backend/app/config.py`
- `backend/app/core/deps.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/router.py`
- `backend/app/schemas/link.py`
- `backend/app/schemas/category.py`
- `backend/app/schemas/tag.py`
- `backend/app/schemas/auth.py`
- `backend/run.py`
- `backend/pyproject.toml`
- `backend/tests/conftest.py`
- `backend/scripts/seed_db.py`

**Frontend:**
- `frontend/src/pages/Landing.tsx`
- `frontend/src/components/ui/index.ts`
- `frontend/src/hooks/index.ts`

**Root:**
- `.agent/prompts/README.md`

---

## Import Path Changes

### Backend Import Changes

**Before:**
```python
from app.models.database import get_db
from app.api.auth import router
```

**After:**
```python
from app.database import get_db
from app.api.v1 import auth
from app.core.deps import get_current_user
from app.schemas.auth import LoginRequest
```

### Frontend Import Changes

**Before:**
```typescript
import Dashboard from './components/Dashboard'
import LinkCard from './components/LinkCard'
```

**After:**
```typescript
import Dashboard from './pages/Dashboard'
import LinkCard from './components/links/LinkCard'
import { useAuth, useDebounce } from './hooks'
```

---

## Configuration Changes

### Docker Compose Service Names

**Before:**
```yaml
services:
  api:
    ...
  web:
    ...
```

**After:**
```yaml
services:
  backend:
    ...
  frontend:
    ...
  redis:    # NEW
    ...
```

---

## Benefits of Migration

1. **Consistency** - Follows established patterns from prompts-hive
2. **Scalability** - Better organized for growth
3. **Maintainability** - Clearer separation of concerns
4. **Testability** - Proper test infrastructure
5. **Versioning** - API versioning for future compatibility
6. **Reusability** - Easier to share code between web and future mobile apps
7. **Developer Experience** - Clearer structure, easier onboarding
8. **Best Practices** - Modern Python tooling, proper schema separation

---

## Risks & Considerations

### Breaking Changes
- All import paths will change
- Docker service names will change
- Environment variables may need updates
- Any existing data/configs need migration

### Mitigation
- Do migration in phases
- Test thoroughly after each phase
- Keep backups before major changes
- Update documentation as we go

---

## Next Steps

1. Create detailed task list in MIGRATION_TASK_TRACKER.md
2. Start with backend restructure (least disruptive)
3. Then frontend restructure
4. Then Docker updates
5. Finally, documentation and tooling

---

*Document created: 2026-01-30*
*Reference project: /Users/mahesh-kulkarni/projects/coding-monkey-labs-hive-projects/cml-prompts-hive*
