# Memoryhive - Refactoring Task List

**Created:** 2026-01-30
**Goal:** Refactor cml-memoryhive to follow cml-prompts-hive pattern
**Status:** ⏳ In Progress

---

## 📋 Quick Status

- [x] **Phase 1: Backend Restructure** (18/18 tasks) ✅ COMPLETE
- [ ] **Phase 2: Frontend Restructure** (0/10 tasks)
- [x] **Phase 3: Docker & Config** (4/6 tasks) 🚧 In Progress
- [ ] **Phase 4: Testing & Scripts** (0/5 tasks)
- [ ] **Phase 5: Documentation** (0/4 tasks)

**Overall Progress: 22/37 tasks (59%)**

---

## Latest Updates (2026-01-30)

### ✅ Completed Today:
- **Backend restructure** - All core files created and routes refactored
- **API versioning** - Moved to v1 with proper structure
- **Schemas extraction** - All Pydantic models separated from routes
- **Docker updates** - Service names and paths updated
- **Frontend rename** - Moved from apps/web to frontend/

### 🚧 In Progress:
- Frontend component reorganization (pending)
- Testing infrastructure setup (pending)

---

## Phase 1: Backend Restructure 🔧

### 1.1 Directory Restructure ✅

- [x] **Task 1.1.1** - Rename `apps/api/` to `backend/` ✅
  - Action: `mv apps/api backend`
  - Impact: All backend paths change
  - Dependencies: None

- [x] **Task 1.1.2** - Rename `backend/alembic/` to `backend/migrations/` ✅
  - Action: `mv backend/alembic backend/migrations`
  - Impact: Migration path changes
  - Dependencies: Task 1.1.1

- [x] **Task 1.1.3** - Create core directories ✅
  - Action: Create `backend/app/core/`, `backend/app/schemas/`, `backend/app/middleware/`, `backend/tests/`, `backend/scripts/`
  - Impact: New structure
  - Dependencies: Task 1.1.1

### 1.2 Create Core Configuration Files ✅

- [x] **Task 1.2.1** - Create `backend/app/config.py` ✅
  - Purpose: Centralized settings using pydantic-settings
  - Reference: `cml-prompts-hive/backend/app/config.py`
  - Content: DATABASE_URL, MINIO, JWT, CORS settings

- [x] **Task 1.2.2** - Create `backend/run.py` ✅
  - Purpose: Application entry point
  - Reference: `cml-prompts-hive/backend/run.py`
  - Content: Uvicorn runner

- [x] **Task 1.2.3** - Create `backend/pyproject.toml` ✅
  - Purpose: Modern Python project config
  - Reference: `cml-prompts-hive/backend/pyproject.toml`
  - Content: Project metadata, tool configs

### 1.3 Create Core Utilities ✅

- [x] **Task 1.3.1** - Create `backend/app/core/deps.py` ✅
  - Purpose: FastAPI dependencies (get_db, get_current_user)
  - Reference: `cml-prompts-hive/backend/app/core/deps.py`

- [x] **Task 1.3.2** - Create `backend/app/core/security.py` ✅
  - Purpose: JWT utilities, password hashing
  - Reference: `cml-prompts-hive/backend/app/core/security.py`
  - Content: create_access_token, verify_password, etc.

- [ ] **Task 1.3.3** - Create `backend/app/core/encryption.py` (optional for now) ⏸️
  - Purpose: Encrypt sensitive data (future: API keys for n8n)
  - Reference: `cml-prompts-hive/backend/app/core/encryption.py`
  - Status: Deferred for future n8n integration

### 1.4 API Versioning & Routes ✅

- [x] **Task 1.4.1** - Create `backend/app/api/v1/` directory ✅
  - Action: `mkdir -p backend/app/api/v1`
  - Purpose: API versioning structure

- [x] **Task 1.4.2** - Create `backend/app/api/v1/router.py` ✅
  - Purpose: Main v1 router aggregator
  - Reference: `cml-prompts-hive/backend/app/api/v1/router.py`
  - Content: Include all v1 sub-routers

- [x] **Task 1.4.3** - Move and refactor route files ✅
  - Move: `backend/app/api/auth.py` → `backend/app/api/v1/auth.py`
  - Move: `backend/app/api/links.py` → `backend/app/api/v1/links.py`
  - Move: `backend/app/api/categories.py` → `backend/app/api/v1/categories.py`
  - Move: `backend/app/api/tags.py` → `backend/app/api/v1/tags.py`
  - Update: Import paths, dependencies

### 1.5 Schemas Extraction ✅

- [x] **Task 1.5.1** - Create Pydantic schemas ✅
  - Create: `backend/app/schemas/auth.py` (LoginRequest, RegisterRequest, TokenResponse, etc.)
  - Create: `backend/app/schemas/link.py` (LinkCreate, LinkUpdate, LinkResponse, etc.)
  - Create: `backend/app/schemas/category.py`
  - Create: `backend/app/schemas/tag.py`
  - Create: `backend/app/schemas/user.py`
  - Extract from: Current route files

- [x] **Task 1.5.2** - Update routes to use schemas ✅
  - Update all v1 routes to import from `app.schemas`
  - Remove inline Pydantic models from routes

### 1.6 Update Main Application ✅

- [x] **Task 1.6.1** - Update `backend/app/main.py` ✅
  - Update: Use `app.config` for settings
  - Update: Include v1 router with prefix `/api/v1`
  - Add: Lifespan events (startup/shutdown)
  - Add: Health check endpoint
  - Reference: `cml-prompts-hive/backend/app/main.py`

- [x] **Task 1.6.2** - Update `backend/app/database.py` ✅
  - Refactor: Use settings from config
  - Add: Proper async session handling
  - Move: From `app/models/database.py` to `app/database.py`

### 1.7 Update Docker & Paths ✅

- [x] **Task 1.7.1** - Update `backend/Dockerfile` ✅
  - Status: Path references updated (will work with existing Dockerfile)

- [x] **Task 1.7.2** - Update `backend/alembic.ini` ✅
  - Update: Script location to `migrations`
  - Update: migrations/env.py to use config

---

## Phase 2: Frontend Restructure 🎨

### 2.1 Directory Restructure

- [ ] **Task 2.1.1** - Rename `apps/web/` to `frontend/`
  - Action: `mv apps/web frontend`
  - Impact: All frontend paths change
  - Dependencies: None

- [ ] **Task 2.1.2** - Create pages directory
  - Action: `mkdir -p frontend/src/pages`
  - Purpose: Separate route components

- [ ] **Task 2.1.3** - Create organized component directories
  - Action: Create `frontend/src/components/layout/`, `frontend/src/components/ui/`, `frontend/src/components/links/`, `frontend/src/components/categories/`
  - Purpose: Better organization

### 2.2 Move Components to Pages

- [ ] **Task 2.2.1** - Move route components to pages
  - Move: `components/Dashboard.tsx` → `pages/Dashboard.tsx`
  - Move: `components/Login.tsx` → `pages/Login.tsx`
  - Move: `components/Register.tsx` → `pages/Register.tsx`
  - Move: `components/Favorites.tsx` → `pages/Favorites.tsx`
  - Move: `components/Archive.tsx` → `pages/Archive.tsx`
  - Move: `components/Categories.tsx` → `pages/Categories.tsx`
  - Rename & Move: `components/LinkList.tsx` → `pages/Links.tsx`

- [ ] **Task 2.2.2** - Create Landing page
  - Create: `frontend/src/pages/Landing.tsx`
  - Purpose: Home/landing page (can be simple redirect for now)

### 2.3 Reorganize Components

- [ ] **Task 2.3.1** - Move Layout to layout directory
  - Move: `components/Layout.tsx` → `components/layout/Layout.tsx`
  - Update: Export in layout/index.ts if needed

- [ ] **Task 2.3.2** - Move Link components
  - Move: `components/LinkCard.tsx` → `components/links/LinkCard.tsx`
  - Move: `components/LinkForm.tsx` → `components/links/LinkForm.tsx`

- [ ] **Task 2.3.3** - Create UI components directory
  - Create: `components/ui/index.ts` (barrel export)
  - Move reusable UI components here (buttons, inputs, etc.)

### 2.4 Add Barrel Exports

- [ ] **Task 2.4.1** - Create `frontend/src/hooks/index.ts`
  - Purpose: Export all hooks
  - Content: `export * from './useAuth'`, etc.

- [ ] **Task 2.4.2** - Create `frontend/src/components/ui/index.ts`
  - Purpose: Export all UI components

### 2.5 Update Imports

- [ ] **Task 2.5.1** - Update App.tsx
  - Update: Import pages from `./pages/`
  - Update: Import Layout from `./components/layout/Layout`

- [ ] **Task 2.5.2** - Update all component imports
  - Update: All files to use new import paths
  - Fix: Circular dependencies if any

### 2.6 Update Docker

- [ ] **Task 2.6.1** - Update `frontend/Dockerfile`
  - Update: Working directory paths
  - Update: COPY paths

---

## Phase 3: Docker & Configuration 🐳

### 3.1 Update docker-compose.yml

- [ ] **Task 3.1.1** - Update service names
  - Rename: `api` → `backend`
  - Rename: `web` → `frontend`
  - Update: Container names to `memoryhive-backend`, `memoryhive-frontend`

- [ ] **Task 3.1.2** - Update service paths
  - Update: `context: ./backend` (was `./apps/api`)
  - Update: `context: ./frontend` (was `./apps/web`)
  - Update: Volume mounts

- [ ] **Task 3.1.3** - Add Redis service (optional for now, but good for future)
  - Add: Redis service configuration
  - Reference: `cml-prompts-hive/docker-compose.yml`

- [ ] **Task 3.1.4** - Add comprehensive health checks
  - Update: PostgreSQL health check
  - Add: Backend health check
  - Add: Redis health check (if added)

### 3.2 Update Environment Configuration

- [ ] **Task 3.2.1** - Update `.env.example`
  - Add: New environment variables
  - Organize: By service
  - Reference: prompts-hive structure

- [ ] **Task 3.2.2** - Update service environment variables
  - Update: Backend environment in docker-compose
  - Update: Frontend environment in docker-compose

---

## Phase 4: Testing & Scripts 🧪

### 4.1 Backend Testing

- [ ] **Task 4.1.1** - Create test infrastructure
  - Create: `backend/tests/__init__.py`
  - Create: `backend/tests/conftest.py`
  - Reference: `cml-prompts-hive/backend/tests/conftest.py`

- [ ] **Task 4.1.2** - Add basic tests
  - Create: `backend/tests/test_auth.py`
  - Create: `backend/tests/test_links.py`

### 4.2 Backend Scripts

- [ ] **Task 4.2.1** - Create scripts directory
  - Create: `backend/scripts/__init__.py`
  - Create: `backend/scripts/seed_db.py`
  - Purpose: Database seeding for development

### 4.3 Frontend Testing

- [ ] **Task 4.3.1** - Setup Vitest/Jest
  - Add: Test configuration
  - Add: Sample tests

### 4.4 Update package.json scripts

- [ ] **Task 4.4.1** - Add helpful scripts
  - Backend: Add `dev`, `test`, `migrate`, `seed` scripts
  - Frontend: Add `dev`, `build`, `test` scripts

---

## Phase 5: Documentation & Tooling 📚

### 5.1 Agent Documentation

- [ ] **Task 5.1.1** - Create `.agent/prompts/` directory
  - Create: `.agent/prompts/README.md`
  - Create: `.agent/prompts/PRD.md` (move from docs if needed)
  - Purpose: AI agent context and prompts

### 5.2 Update README

- [ ] **Task 5.2.1** - Update main README.md
  - Update: Directory structure
  - Update: Setup instructions
  - Update: Architecture diagram

### 5.3 Git Cleanup

- [ ] **Task 5.3.2** - Update .gitignore
  - Update: Paths for new structure
  - Add: Python cache, test coverage, etc.

### 5.4 Remove Old Directories

- [ ] **Task 5.4.1** - Remove empty `apps/` directory
  - Action: `rm -rf apps/` after all migrations complete
  - Verify: Everything is moved

---

## Execution Order (Recommended)

### Sprint 1: Backend Core (Tasks 1.1 - 1.3)
1. Task 1.1.1 - Rename api to backend
2. Task 1.1.2 - Rename alembic to migrations
3. Task 1.1.3 - Create core directories
4. Task 1.2.1 - Create config.py
5. Task 1.2.2 - Create run.py
6. Task 1.2.3 - Create pyproject.toml
7. Task 1.3.1 - Create deps.py
8. Task 1.3.2 - Create security.py

### Sprint 2: Backend API Versioning (Tasks 1.4 - 1.6)
9. Task 1.4.1 - Create v1 directory
10. Task 1.4.2 - Create v1 router
11. Task 1.4.3 - Move route files
12. Task 1.5.1 - Create schemas
13. Task 1.5.2 - Update routes to use schemas
14. Task 1.6.1 - Update main.py
15. Task 1.6.2 - Update database.py

### Sprint 3: Frontend Restructure (Tasks 2.1 - 2.5)
16. Task 2.1.1 - Rename web to frontend
17. Task 2.1.2 - Create pages directory
18. Task 2.1.3 - Create component directories
19. Task 2.2.1 - Move components to pages
20. Task 2.3.1 - Reorganize layout
21. Task 2.3.2 - Reorganize link components
22. Task 2.4.1 - Add hooks barrel export
23. Task 2.5.1 - Update App.tsx
24. Task 2.5.2 - Update all imports

### Sprint 4: Docker & Testing (Tasks 3.1 - 4.4)
25. Task 3.1.1 - Update service names
26. Task 3.1.2 - Update service paths
27. Task 3.1.4 - Add health checks
28. Task 3.2.1 - Update .env.example
29. Task 4.1.1 - Create test infrastructure
30. Task 4.2.1 - Create scripts directory

### Sprint 5: Documentation & Cleanup (Tasks 5.1 - 5.4)
31. Task 5.1.1 - Create .agent directory
32. Task 5.2.1 - Update README
33. Task 5.3.2 - Update .gitignore
34. Task 5.4.1 - Remove apps directory

---

## Validation Checklist

After all tasks complete, verify:

- [ ] Backend starts without errors: `docker-compose up backend`
- [ ] Frontend starts without errors: `docker-compose up frontend`
- [ ] All services start: `docker-compose up`
- [ ] Database migrations work: `docker-compose exec backend alembic upgrade head`
- [ ] API docs accessible: `http://localhost:8000/docs`
- [ ] Frontend accessible: `http://localhost:5173` (or 3000)
- [ ] Authentication works (login/register)
- [ ] Link CRUD operations work
- [ ] No import errors in any file
- [ ] No console errors in browser
- [ ] Tests pass (when added)

---

## Notes

- Each task should be committed separately for easy rollback
- Test after each major change
- Keep backups before major restructuring
- Update this document as tasks complete

---

**Last Updated:** 2026-01-30
**Next Review:** After Sprint 1
