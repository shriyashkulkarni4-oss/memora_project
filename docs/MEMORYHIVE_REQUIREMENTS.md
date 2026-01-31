# Memoryhive – Product Requirements Document (PRD)

Version: 1.0  
Status: MVP Definition  
Owner: Product / Engineering  

---

## 1. Product Overview

### Product Name
Memoryhive

### Tagline
Never lose a useful thought again.

### Product Summary
Memoryhive is a mobile-first, offline-first personal capture and recall application.  
It allows users to save screenshots, links, and text, and automatically converts them into organized, searchable, and retrievable knowledge.

Memoryhive focuses on **capture → understanding → recall**, without forcing users to manually organize content.

---

## 2. Problem Statement

Users frequently encounter valuable information across:
- News articles
- Social media posts (LinkedIn, Twitter/X)
- Screenshots
- Blogs, videos, research references

Existing solutions fail because:
- Screenshots are not searchable
- Bookmarks lack context
- Notes require manual effort
- Information is scattered across apps
- Recall degrades rapidly over time

Result: Valuable information is lost or never reused.

---

## 3. Goals and Success Criteria

### Primary Goal
Allow users to capture information once and recall it effortlessly later.

### Success Criteria
- Capture content in under 2 seconds
- Automatic understanding without manual tagging
- Search works across text, screenshots, and links
- App usable without internet connection
- User trusts data privacy and ownership

---

## 4. Target Users

### Primary Users
- Knowledge workers
- Founders and builders
- Researchers
- Curious professionals
- Heavy screenshot and bookmark users

### Non-Target Users
- Task / reminder focused users
- Social media content creators
- Collaboration-heavy teams
- Project management users

---

## 5. Core Use Cases

1. Save a screenshot and later search its content
2. Save an article link and get a short summary
3. Revisit previously saved insights
4. Search saved content by keyword, source, or time
5. Use the app completely offline

---

## 6. Core Principles

- Mobile-first
- Offline-first
- Local data ownership
- Minimal user effort
- AI is background assistance, not a requirement

---

## 7. Functional Requirements

### 7.1 Capture

#### Supported Inputs
- Screenshots (from share sheet)
- URLs / hyperlinks
- Plain text

#### Capture Requirements
- Single-tap save from share menu
- No mandatory metadata input
- Instant local save

---

### 7.2 Processing (Background)

#### Screenshot Processing
- OCR extraction
- Language detection
- Text normalization

#### Link Processing
- Fetch readable content
- Remove ads and clutter
- Extract title, author, date (if available)

#### AI Processing (Optional)
- Auto summary (short)
- Auto tag suggestions
- Content classification

Processing must:
- Run asynchronously
- Work offline when local models are available
- Never block capture flow

---

### 7.3 Storage

#### Local Storage
- All raw content stored locally by default
- Indexed for search

#### Cloud Sync (Optional)
- User-owned backend
- Encrypted at rest
- Sync conflicts resolved locally

---

### 7.4 Viewing & Organization

#### Content View
- Card-based list
- Shows:
  - Title
  - Short summary
  - Source
  - Timestamp

#### Organization Rules
- No mandatory folders
- Tags are auto-generated
- Manual tags optional

---

### 7.5 Search & Recall

#### Search Capabilities
- Full-text search
- Screenshot text search
- Source-based filtering
- Time-based filtering

#### Recall Features
- Recently resurfaced items
- Contextual reminders (non-intrusive)

---

## 8. Non-Functional Requirements

### Performance
- App launch under 2 seconds
- Capture action under 500ms

### Offline Capability
- Full capture and search offline
- Sync resumes when online

### Privacy & Security
- No ads
- No data selling
- User can delete/export all data
- Clear privacy policy

---

## 9. Explicit Non-Goals (What NOT to Build)

- Task management
- Reminders and notifications
- Collaboration or sharing feeds
- Public collections
- Markdown editors
- Chat with notes (v1)
- Folder-heavy organization
- Calendar integration

---

## 10. Technical Architecture (High-Level)

### Client
- Android App
- iOS App
- Lightweight Web Viewer (optional)

### Backend
- Authentication service
- Metadata API
- Sync service

### Storage
- Object Storage: MinIO (S3-compatible)
- Database: PostgreSQL

### AI Pipeline (Optional)
- n8n for orchestration
- Local LLM (Ollama)
- OCR engine

---

## 11. Data Model (High-Level)

### User
- user_id
- email
- created_at

### Item
- item_id
- user_id
- type (screenshot, link, text)
- raw_content
- extracted_text
- summary
- tags
- source
- created_at

### Asset
- asset_id
- item_id
- storage_path
- mime_type

---

## 12. App Distribution

### Platforms
- Google Play Store
- Apple App Store

### Category
- Productivity

### Monetization (Future)
- Free tier with limits
- Paid sync / advanced AI features

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|----|----|
| Feature creep | Strict non-goals |
| AI latency | Async processing |
| Trust issues | Local-first, transparency |
| Sync conflicts | Client-side resolution |

---

## 14. MVP Definition

MVP includes:
- Capture screenshots, links, text
- Local storage
- OCR + text extraction
- Search
- Simple list view

Everything else is optional.

---

## 15. Guiding Product Rule

If a feature does not improve **capture, understanding, or recall**, it does not belong in Memoryhive.\


## UNSTRUCTURED - RAW PROMPT
```
problem we are solving
I am looking for some simple app, where i can keep adding the Screenshots, hyperlinks of news articles, LinkedIn posts, twitter etc

i want to build this as a Android and apple app, so i can help others too.

This app would maintain things on mobile itself… it will also have a small webapp, a backend to store data etc

now whats the beauty…
app just solves one problem..
How do i manage my help links
When i have too many of such bookmarks, not able to manage and benefit from these things
AI angle…
Different app using a n8n pipeline, simple

offline, we can build a small n8n pipeline, tuns with my own ollama etc…
it would review the links shared
Scan screenshots and bring its data back
Analyze the links shared and connect the links and bring back their summary etc.
So we end up showing good categorisation and summary too
Db Design…
very simple…

minio S3 for Document uploads
postgres for users, their links, their summaries
Refer
This app is similar to the PromptHive, lets use same base

Start building this whole things…
This is for me but i am fully positive of publishing this app, webapp etc
```