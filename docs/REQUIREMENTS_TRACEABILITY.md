# Requirements Traceability

Last audited: 2026-09-05

| Requirement | Implementation | Status |
|---|---|---|
| Link, screenshot, and text capture | Web capture flows, native share intent, `/api/v1/items` | Complete |
| Instant offline capture and search | Expo SQLite store and queued mutations | Complete |
| OCR, language detection, normalization | Durable Tesseract processing worker | Complete |
| Link title, author, date, readable text | SSRF-protected metadata/content extractor | Complete |
| Optional summary, classification, tags | n8n/Ollama adapter; capture does not depend on it | Complete, optional service |
| Card list and item detail | Responsive web and Expo library/detail screens | Complete |
| Full-text screenshot/link/text search | PostgreSQL search plus local mobile search | Complete |
| Source and time filtering | Versioned API filters | Complete |
| Recently saved/resurfaced content | Recency-ordered library and recent dashboard | MVP complete |
| Offline reconnect sync | Change feed, mutation queue, tombstones, revisions | Complete |
| Export and delete all data | Portable ZIP export and password-confirmed deletion | Complete |
| Private ownership and production security | Owner-scoped API, private assets, TLS, headers, rate limits | Complete |
| iOS and Android distribution | Expo/EAS identifiers and release profiles | Prepared; credentials required |

## Deliberate boundaries

- End-to-end encryption is not implemented. Production encryption at rest is an
  infrastructure responsibility, as defined in the implementation plan.
- Reminder notifications are excluded from v1. In-app recency is the recall
  mechanism, consistent with the explicit non-goal for reminders.
- AI enrichment needs an operator-provided n8n or Ollama endpoint. OCR and core
  search remain functional without it.
- Public hosting and app-store submission remain external release actions; all
  repository artifacts and checklists are prepared.
