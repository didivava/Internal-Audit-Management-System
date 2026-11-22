# Northstar Audit: implementation plan

## Confirmed direction

- **Application:** browser-based internal audit management system.
- **Backend:** Django modular monolith.
- **Database:** PostgreSQL.
- **Identity:** organization-managed OpenID Connect (OIDC) SSO with Microsoft Entra ID.
- **Hosting:** organization-approved cloud; provider and deployment environment are still to be selected.
- **Current product:** a frontend prototype with browser-local demo data. Do not enter real audit data until server-side authorization, storage, and audit controls are implemented and reviewed.

## Confirmed methodology and workflow defaults

- Align the product to the IIA Global Internal Audit Standards while allowing organization-specific methodology and approvals.
- Use the prototype's initial inherent-risk bands: score = likelihood × impact (both 1–5); 1–5 Low, 6–11 Medium, 12–19 High, 20–25 Critical.
- Start with auditors drafting, an audit manager reviewing, the Chief Audit Executive approving plans/reports, control owners responding to findings, and auditors validating actions before closure. These role assignments must be checked against the organization's segregation-of-duties rules.
- Data classification, evidence retention, legal hold, privacy, and residency requirements are not decided. The initial schema stores evidence metadata only; do not upload real evidence until these policies and an approved object-storage design exist.

## Delivery sequence

### Step 1 — Application foundation (in progress)

- Establish Django configuration, environment-driven PostgreSQL settings, containerized local development, static asset serving, and liveness/readiness endpoints.
- Keep debug-only SQLite available for a lightweight local check; PostgreSQL is required outside debug mode.
- Gate: automated tests pass, PostgreSQL-backed readiness succeeds locally, and production settings reject missing secrets, hosts, or a PostgreSQL URL.
- Current status: all 33 Django tests, system checks, migration consistency, and dependency checks pass on local SQLite. The PostgreSQL-backed smoke test is pending because this development environment has no Docker or local PostgreSQL executable.

### Step 2 — Audit domain and governance

- Confirm audit methodology, risk-scoring thresholds, finding severity, engagement lifecycle, approval roles, records retention, data classification, and audit-log requirements with Audit, Legal, Privacy, Security, and Records Management.
- Model auditable entities, risk assessments, annual plans, engagements, work programs, workpapers/evidence metadata, findings, management responses, action plans, reviews, and append-only audit events. The initial Django models and migrations are now implemented; risk thresholds use the confirmed prototype bands.
- Add migrations, constraints, ownership rules, and tests before importing business data.
- Gate: domain owners approve the schema and data lifecycle; migrations and integrity tests pass on PostgreSQL.
- Current status: initial custom-user and audit-domain models/migrations are implemented and covered by the passing Django suite. PostgreSQL migration validation and retention/data-classification decisions are outstanding.

### Step 3 — Identity and authorization

- Select the organization OIDC provider and agree on callback/logout URLs, supported claims, group/role mapping, MFA policy, account provisioning, and emergency access.
- Integrate OIDC; enforce least-privilege roles and engagement-level access on every server request.
- Gate: authorization tests cover auditors, managers, action owners, administrators, restricted engagements, and denied cross-engagement access. SSO configuration must use an approved test tenant.
- Current status: Microsoft Entra OIDC login/callback scaffolding is implemented with PKCE, nonce, RS256 signature verification, and explicit issuer/audience/tenant/time validation. A simulated login redirect is tested, but a real login is not verified: the Entra tenant/app registration, client secret, role values, and production redirect URI have not been supplied. The current endpoint configuration targets Microsoft's public cloud; confirm before using a sovereign cloud. An authenticated audit-plan API now enforces role-based and assignment-scoped access; authorization for other audit records remains to be implemented.

### Step 4 — Server-backed workflows

- Expose validated Django endpoints for planning, fieldwork, findings, management responses, follow-up, and risk assessment.
- Replace browser-local records with API data; retain search, filters, dashboards, and export behavior where approved.
- Gate: API and browser tests prove workflow transitions, approval checks, export permissions, and persistence across users and sessions.
- Current status: the first API slice provides paginated audit-plan reads/writes, auditor and executive read scopes, manager submission, CAE approval, and audit events for plan changes. UI integration and APIs for engagements, findings, and actions remain outstanding.

### Step 5 — Evidence, integrations, and reporting

- Add private object storage with malware scanning, size/type controls, access checks, retention, and download auditing.
- Add approved read-only integrations and reporting only after source-system owners approve data contracts and reconciliation rules.
- Gate: threat model and data-flow review, evidence-access tests, retention tests, and reconciliation sign-off.

### Step 6 — Production readiness and rollout

- Select cloud provider, region, network boundaries, secret manager, managed PostgreSQL, object storage, backups, restore objectives, logging/monitoring, and deployment pipeline.
- Add operational runbooks, incident response, access reviews, recovery tests, security testing, migration plan, training, pilot acceptance, and rollback.
- Gate: security/privacy/legal sign-off, restore exercise, monitoring alerts verified, pilot criteria met, and production SSO/storage configured.

## Decisions needed before later gates

1. Approved cloud provider, region, runtime, and network/security baseline.
2. Entra tenant ID, app registration, public or sovereign cloud, role values, group/role owners, and production callback URI.
3. Audit methodology and approval paths.
4. Data classification, evidence retention, legal hold, export, and deletion rules.
5. Availability, recovery-time, recovery-point, and expected user-volume targets.
6. ERP, HR, identity, document-management, and risk-system integration priorities.
7. Production DNS/subdomain ownership and whether HSTS should cover subdomains or be preload eligible.

## Identity implementation references

- [Microsoft identity platform OpenID Connect protocol](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc)
- [Microsoft Entra ID token claims](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference)
- [mozilla-django-oidc installation and configuration](https://mozilla-django-oidc.readthedocs.io/en/stable/installation.html)

## Current step boundary

This project is not a production deployment. It does not provide verified organization SSO, complete authorization for all audit records, complete audit-event capture, database-enforced event immutability, or secure evidence storage. Authorization and event recording currently cover audit-plan API operations only. Those controls are deliberate prerequisites to storing real audit information.
