# Memoryhive - Migration & Refactoring Task Tracker

**Created:** 2026-01-30
**Status:** Planning Phase
**Target:** Refactor to follow cml-prompts-hive pattern

---

## Overview

This document tracks the migration of cml-memoryhive from its current state (Claude Code Web generated) to a production-ready application following the cml-prompts-hive architectural pattern.

**Current Completion:** ~45%
**Target:** MVP (Mobile-first, Offline-first)

---

## Phase 1: Project Structure Refactoring

### 1.1 Analyze Reference Pattern
- [ ] **Study cml-prompts-hive structure** - Understand folder organization, naming conventions, and architectural patterns
- [ ] **Document key differences** - Create comparison document between current cml-memoryhive and prompts-hive
- [ ] **Identify reusable patterns** - Extract patterns for monorepo, Docker setup, API structure, etc.

### 1.2 Monorepo Restructuring
- [ ] **Update root structure** - Align with prompts-hive pattern (packages, apps, shared)
- [ ] **Create packages directory** - For shared code between web/mobile (types, utils, constants)
- [ ] **Reorganize apps directory** - Follow consistent naming and structure
- [ ] **Setup workspace management** - Update package.json for monorepo tooling (npm workspaces, pnpm, or yarn)

### 1.3 Configuration Standardization
- [ ] **Align Docker setup** - Match docker-compose patterns from prompts-hive
- [ ] **Standardize environment files** - .env structure, variable naming conventions
- [ ] **Update build configs** - Vite, TypeScript, linting, formatting configs
- [ ] **Add development tooling** - Scripts for dev, build, test, deploy

---

## Phase 2: Backend (API) Refactoring

### 2.1 Project Structure
- [ ] **Reorganize FastAPI structure** - Follow prompts-hive backend pattern
- [ ] **Update routing patterns** - API versioning, consistent endpoint naming
- [ ] **Refactor models** - Align SQLAlchemy models with best practices
- [ ] **Improve services layer** - Separate business logic from API routes

### 2.2 Database & Storage
- [ ] **Review database schema** - Optimize for offline-first, sync requirements
- [ ] **Add migration strategy** - Document migration approach for existing data
- [ ] **Enhance MinIO integration** - Add chunked uploads, compression, CDN support
- [ ] **Add indexing strategy** - Full-text search indexes for PostgreSQL

### 2.3 Authentication & Security
- [ ] **Review JWT implementation** - Refresh tokens, expiry handling
- [ ] **Add rate limiting** - Protect API endpoints
- [ ] **Implement CORS properly** - Production-ready CORS config
- [ ] **Add request validation** - Pydantic schemas for all endpoints

### 2.4 API Enhancements
- [ ] **Add webhook endpoints** - For n8n integration
- [ ] **Implement batch operations** - Bulk upload, delete, update
- [ ] **Add export endpoints** - Data export (JSON, CSV)
- [ ] **Add health/status endpoints** - Monitoring and healthchecks

---

## Phase 3: Frontend (Web) Refactoring

### 3.1 Project Structure
- [ ] **Align with prompts-hive pattern** - Component organization, folder structure
- [ ] **Create shared components** - Extract reusable UI components
- [ ] **Organize by feature** - Feature-based folder structure vs component-based
- [ ] **Add component library** - Storybook or similar for component documentation

### 3.2 State Management
- [ ] **Review Zustand implementation** - Ensure proper patterns, persistence
- [ ] **Add offline state sync** - Queue actions when offline, sync when online
- [ ] **Implement optimistic updates** - Better UX for create/update/delete
- [ ] **Add error boundaries** - Graceful error handling

### 3.3 API Integration
- [ ] **Connect to real API** - Replace all mock data
- [ ] **Add request caching** - React Query or SWR for data fetching
- [ ] **Implement retry logic** - Handle network failures gracefully
- [ ] **Add loading states** - Skeleton screens, spinners, progress indicators

### 3.4 UI/UX Improvements
- [ ] **Mobile-responsive design** - Ensure works well on mobile browsers
- [ ] **Add keyboard shortcuts** - Power user features
- [ ] **Implement drag & drop** - For file uploads, reordering
- [ ] **Add dark mode** - Theme switching capability

---

## Phase 4: Mobile App (React Native) - NEW

### 4.1 Project Setup
- [ ] **Initialize React Native project** - Create apps/mobile
- [ ] **Setup navigation** - React Navigation with proper structure
- [ ] **Configure build tools** - Metro bundler, build scripts
- [ ] **Setup development environment** - iOS and Android emulators

### 4.2 Shared Code Extraction
- [ ] **Extract types to packages** - Shared TypeScript types
- [ ] **Extract API client** - Shared API service layer
- [ ] **Extract constants** - Shared enums, constants, configs
- [ ] **Extract utilities** - Date formatting, validation, etc.

### 4.3 Core Features
- [ ] **Authentication flow** - Login, register, token management
- [ ] **Link capture** - Share sheet integration (iOS/Android)
- [ ] **Screenshot capture** - Camera integration, gallery picker
- [ ] **Link listing** - Infinite scroll, pull-to-refresh
- [ ] **Search interface** - Full-text search UI
- [ ] **Offline storage** - SQLite/WatermelonDB for local data

### 4.4 Native Features
- [ ] **Share extension** - iOS/Android share targets
- [ ] **Camera integration** - Direct screenshot capture
- [ ] **File system access** - Local file management
- [ ] **Background sync** - Sync when app is in background
- [ ] **Push notifications** - (Optional) Processing complete notifications

### 4.5 Platform-Specific
- [ ] **iOS specific** - App icons, splash screens, permissions
- [ ] **Android specific** - App icons, splash screens, permissions
- [ ] **App store assets** - Screenshots, descriptions, metadata

---

## Phase 5: AI Pipeline (n8n Integration)

### 5.1 Infrastructure
- [ ] **Add n8n to docker-compose** - New service container
- [ ] **Setup n8n persistence** - Workflow storage, credentials
- [ ] **Configure n8n access** - Authentication, webhook endpoints
- [ ] **Connect to Ollama** - Local LLM integration

### 5.2 Workflows
- [ ] **Screenshot OCR workflow** - Tesseract/Ollama vision extraction
- [ ] **Link metadata workflow** - Fetch OG tags, favicon, title
- [ ] **Content summarization workflow** - AI-generated summaries
- [ ] **Auto-categorization workflow** - Suggest categories and tags
- [ ] **Webhook triggers** - API → n8n → API callback flow

### 5.3 Backend Integration
- [ ] **Add webhook endpoints** - Trigger n8n workflows
- [ ] **Add callback endpoints** - Receive processed data from n8n
- [ ] **Add job queue** - Track processing status
- [ ] **Add retry mechanism** - Handle failed processing

### 5.4 Frontend Integration
- [ ] **Show processing status** - UI indicators for AI processing
- [ ] **Display AI results** - Summaries, tags, categories
- [ ] **Allow editing AI results** - User can modify suggestions
- [ ] **Add processing history** - View AI processing logs

---

## Phase 6: Offline-First Implementation

### 6.1 Web App Offline
- [ ] **Service Worker setup** - PWA capabilities
- [ ] **Cache strategies** - Cache-first for assets, network-first for data
- [ ] **Offline detection** - UI indicators for online/offline state
- [ ] **Sync queue** - Queue operations when offline

### 6.2 Mobile App Offline
- [ ] **Local database** - SQLite/WatermelonDB/Realm
- [ ] **Data synchronization** - Sync strategy (last-write-wins, CRDT)
- [ ] **Conflict resolution** - Handle sync conflicts
- [ ] **Background sync** - Periodic sync in background

### 6.3 Sync Protocol
- [ ] **Define sync API** - RESTful or custom sync protocol
- [ ] **Implement delta sync** - Only sync changed data
- [ ] **Add versioning** - Track data versions for conflict resolution
- [ ] **Add sync status UI** - Show last sync time, pending changes

---

## Phase 7: Testing & Quality

### 7.1 Backend Testing
- [ ] **Unit tests** - Services, utilities
- [ ] **Integration tests** - API endpoints
- [ ] **Database tests** - Model operations, migrations
- [ ] **Load testing** - API performance under load

### 7.2 Frontend Testing
- [ ] **Unit tests** - Components, hooks, utilities
- [ ] **Integration tests** - User flows
- [ ] **E2E tests** - Playwright/Cypress
- [ ] **Visual regression tests** - Chromatic or similar

### 7.3 Mobile Testing
- [ ] **Unit tests** - Business logic, utilities
- [ ] **Component tests** - React Native components
- [ ] **E2E tests** - Detox for iOS/Android
- [ ] **Device testing** - Test on real devices

### 7.4 Quality Assurance
- [ ] **Code coverage** - Maintain >80% coverage
- [ ] **Linting** - ESLint, Pylint
- [ ] **Type checking** - TypeScript strict mode, mypy
- [ ] **Security scanning** - Dependency vulnerabilities

---

## Phase 8: DevOps & Production

### 8.1 CI/CD Pipeline
- [ ] **Setup GitHub Actions** - Automated testing, building
- [ ] **Setup build pipelines** - Web, API, Mobile builds
- [ ] **Setup deployment** - Automated deployments
- [ ] **Add staging environment** - Separate staging from production

### 8.2 Production Infrastructure
- [ ] **Production docker-compose** - Optimized for production
- [ ] **SSL/TLS setup** - HTTPS for API and web
- [ ] **Reverse proxy** - Nginx or Traefik
- [ ] **Database backups** - Automated backup strategy
- [ ] **File storage backups** - MinIO backup strategy

### 8.3 Monitoring & Logging
- [ ] **Application monitoring** - Sentry for error tracking
- [ ] **Performance monitoring** - API response times, database queries
- [ ] **Logging infrastructure** - Centralized logging (ELK, Grafana Loki)
- [ ] **Alerting** - Critical error alerts

### 8.4 Mobile App Distribution
- [ ] **iOS TestFlight** - Beta testing setup
- [ ] **Android internal testing** - Play Console setup
- [ ] **App Store submission** - iOS App Store
- [ ] **Play Store submission** - Android Play Store

---

## Phase 9: Documentation

### 9.1 Developer Documentation
- [ ] **Architecture docs** - System architecture, data flow
- [ ] **API documentation** - OpenAPI/Swagger docs
- [ ] **Setup guides** - Development environment setup
- [ ] **Contributing guide** - Code standards, PR process

### 9.2 User Documentation
- [ ] **User guide** - How to use the app
- [ ] **FAQ** - Common questions
- [ ] **Privacy policy** - Data handling, privacy
- [ ] **Terms of service** - Legal terms

### 9.3 Deployment Documentation
- [ ] **Deployment guide** - Production deployment steps
- [ ] **Maintenance guide** - Backup, restore, updates
- [ ] **Troubleshooting guide** - Common issues and solutions
- [ ] **Monitoring guide** - How to use monitoring tools

---

## Phase 10: MVP Release Checklist

### 10.1 Core Features (MUST HAVE)
- [ ] ✅ User authentication (login, register)
- [ ] ✅ Save links with metadata
- [ ] ✅ Upload screenshots
- [ ] ✅ Basic categorization and tags
- [ ] ✅ Search functionality
- [ ] ✅ Web app functional
- [ ] ❌ Mobile app (iOS & Android)
- [ ] ❌ Offline-first capability
- [ ] ❌ Screenshot OCR
- [ ] ❌ Link metadata extraction

### 10.2 Quality Checklist
- [ ] ❌ All tests passing
- [ ] ❌ Security audit complete
- [ ] ❌ Performance benchmarks met
- [ ] ❌ Mobile app responsive
- [ ] ❌ Offline mode works

### 10.3 Production Readiness
- [ ] ❌ Production infrastructure setup
- [ ] ❌ SSL/TLS configured
- [ ] ❌ Backups automated
- [ ] ❌ Monitoring in place
- [ ] ❌ Error tracking setup

### 10.4 Legal & Compliance
- [ ] ❌ Privacy policy written
- [ ] ❌ Terms of service written
- [ ] ❌ App store compliance
- [ ] ❌ GDPR compliance (if applicable)

---

## Current Status Summary

| Phase | Status | Completion % |
|-------|--------|--------------|
| Phase 1: Project Structure | Not Started | 0% |
| Phase 2: Backend Refactoring | Partially Done | 60% |
| Phase 3: Frontend Refactoring | Partially Done | 70% |
| Phase 4: Mobile App | Not Started | 0% |
| Phase 5: AI Pipeline | Not Started | 0% |
| Phase 6: Offline-First | Not Started | 0% |
| Phase 7: Testing & Quality | Not Started | 0% |
| Phase 8: DevOps & Production | Minimal | 10% |
| Phase 9: Documentation | Minimal | 20% |
| Phase 10: MVP Release | In Progress | 45% |

**Overall Project Completion: ~45%**
**Estimated MVP Completion: ~25%** (because mobile app and offline-first are critical)

---

## Priority Order (Recommended)

### Immediate (Next 2 weeks)
1. **Analyze cml-prompts-hive pattern** - Understand reference architecture
2. **Restructure project** - Align with prompts-hive patterns
3. **Extract shared packages** - Prepare for mobile app
4. **Setup React Native project** - Begin mobile development

### Short-term (Next 4 weeks)
5. **Implement mobile core features** - Auth, capture, listing
6. **Add offline storage** - SQLite/local database
7. **Implement sync mechanism** - Basic online/offline sync
8. **Add share extensions** - iOS/Android share targets

### Medium-term (Next 8 weeks)
9. **Setup n8n pipeline** - AI processing infrastructure
10. **Implement OCR** - Screenshot text extraction
11. **Implement link scraper** - Metadata extraction
12. **Add AI summaries** - Content summarization

### Long-term (Next 12 weeks)
13. **Complete testing** - All test suites
14. **Production infrastructure** - Deploy to production
15. **App store submission** - iOS and Android
16. **Beta testing** - TestFlight and Play Console

---

## Notes

- This tracker will be updated as we progress through the migration
- Each phase should have its own detailed subtasks as needed
- Priority may shift based on user feedback and requirements
- Reference to cml-prompts-hive pattern needs to be established first

---

*Last Updated: 2026-01-30*
