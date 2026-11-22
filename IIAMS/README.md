# Northstar Audit

An internal audit management application in active development. The browser workspace is still a prototype; the Django/PostgreSQL foundation is being added in stages.

## Run locally

### Django with local SQLite

```sh
python3 -m pip install -e .
DJANGO_DEBUG=true python manage.py migrate
DJANGO_DEBUG=true python manage.py test
DJANGO_DEBUG=true python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000). The demo workspace is served only with `DJANGO_DEBUG=true`; production mode intentionally returns `503` until authentication and the server-backed workflows are production-ready. SQLite is for development checks only; PostgreSQL is required whenever debug mode is disabled.

## Configuration and health checks

- Production requires a unique `DJANGO_SECRET_KEY` with at least 50 characters, explicit non-wildcard `DJANGO_ALLOWED_HOSTS`, and a PostgreSQL `DATABASE_URL`; configuration fails closed when these are missing.
- Production PostgreSQL connections use `sslmode=require` unless the URL specifies an `sslmode` query parameter or `DATABASE_SSLMODE` overrides it.
- Production defaults to secure session/CSRF cookies, HSTS, and HTTPS redirects. Set `DJANGO_TRUST_PROXY_SSL=true` only when a trusted ingress strips client-supplied forwarding headers and sets `X-Forwarded-Proto`. Decide whether HSTS should include subdomains or be preload eligible only after confirming domain ownership and HTTPS coverage.
- `GET /health/live/` checks that the web process responds. `GET /health/ready/` also checks the configured database.
- Production also requires `ENTRA_TENANT_ID` (tenant GUID), `ENTRA_CLIENT_ID`, and `ENTRA_CLIENT_SECRET`. Set the secret through the approved secret manager, never in source control. Register `https://<approved-host>/oidc/callback/` as the app's redirect URI.
- Entra role values can be mapped to Django groups with `ENTRA_ROLE_GROUP_MAPPING`, a JSON object such as `{"Audit.Manager":"audit_manager"}`. This defaults to no role grants; only map approved app roles, and do not rely on email addresses as identity keys.
- OIDC currently targets Microsoft's public cloud. Do not use this configuration for a sovereign cloud without reviewing and changing the authority and Graph endpoints.

### PostgreSQL with Docker Compose

```sh
cp .env.example .env
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The Compose database and credentials are for local development only.

## Current functionality

The existing UI has an overview, audit plan, findings, action tracking, and risk register, with sample records, search, filters, CSV/JSON exports, and browser-local persistence. Those records have not yet been migrated to Django. Django has initial models for users, audit plans, auditable entities, risks/assessments, engagements, work programs, workpaper metadata/reviews, findings, management responses, action plans/validation, and append-only audit events. The authenticated `/api/v1/audit-plans/` API supports scoped plan access, manager submission, CAE approval, and event recording; the browser UI is not connected to it yet.

## Security boundary

Do not enter real or confidential audit information. Entra OIDC scaffolding is implemented, but no organization tenant/app registration has been configured or used for a real sign-in. Authorization and event recording currently cover only the audit-plan API; other records and the browser UI are not yet server-backed. Secure evidence storage and tamper-resistant audit logging are not implemented. The audit-event model blocks edits through Django model/queryset APIs, but database owners can still change its rows; production-grade immutability requires additional database/operational controls. Read the [implementation plan](docs/implementation-plan.md) for delivery gates and unresolved organization-specific decisions.
