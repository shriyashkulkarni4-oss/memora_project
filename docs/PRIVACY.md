# Memoryhive Privacy Policy

Last updated: 2026-09-05

Memoryhive stores the account details and content needed to provide capture,
search, synchronization, export, and processing. Saved content can include URLs,
notes, screenshots, extracted text, tags, and generated summaries.

## Data handling

- Account and item metadata is stored in PostgreSQL. Screenshot files are stored
  in private MinIO buckets and are served through authenticated API requests.
- The mobile client keeps a local SQLite copy so capture and search work offline.
- Link processing requests the saved URL from the Memoryhive server. Optional
  n8n or Ollama integrations receive content only when an operator configures
  those services.
- Request logs contain method, path, response status, duration, and request ID.
  Request bodies and authorization tokens are not logged by the application.
- Memoryhive does not contain advertising or data-sale integrations.

## Control and retention

Users can download a portable ZIP export from Settings and can permanently
delete their account after password confirmation. Item deletion creates a sync
tombstone; account deletion removes database records and schedules associated
objects for deletion. Operational backups are retained for 14 days by default,
so deleted information can remain in encrypted, access-controlled backups until
those backups expire.

Self-hosting operators control infrastructure location, encryption at rest,
backup access, retention, and any optional processing integrations. Production
operators must publish their contact details and jurisdiction-specific terms
before accepting public registrations.

## Security and requests

Traffic to a production deployment is protected with TLS. Application access is
authenticated and records are scoped to their owner. To request access,
correction, export, or deletion, use the in-app controls or contact the operator
of the deployed instance.
