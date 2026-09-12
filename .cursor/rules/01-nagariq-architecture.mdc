---
description: Core architecture and development rules for NagarIQ
alwaysApply: true
---

# NagarIQ Architecture Rules

## Project

NagarIQ is a Municipal Intelligence & Accountability Platform for the Solapur municipal complaint workflow.

The system has exactly two primary applications:

1. Mobile App
   - Citizen
   - Field Worker
   - Role-based navigation

2. Web App
   - Municipal Admin
   - Department / Operations
   - Role-based dashboards and permissions

---

## Technology

Mobile:
React Native + Expo

Web:
Next.js

Backend:
FastAPI

Database:
PostgreSQL + PostGIS

Optional:
pgvector

---

## Core Complaint Lifecycle

Citizen creates complaint
→ Photo + Text + GPS
→ Ward / Zone determination
→ Classification
→ Severity
→ Priority
→ Department review
→ Assignment
→ Field worker action
→ Worker notes / support request
→ Resolution evidence
→ Verification
→ Citizen confirmation
→ Closure
→ Audit history

Every feature should preserve this lifecycle.

---

## Roles

Supported roles:

- CITIZEN
- FIELD_WORKER
- DEPARTMENT_OFFICER
- ADMIN

Authorization MUST be enforced by the backend.

Frontend hiding is not authorization.

---

## Complaint Status

Use an explicit status machine.

Do not allow arbitrary status transitions.

Every important status transition must be auditable.

---

## Assignment

`complaints.assigned_to` represents the CURRENT assignee.

Historical assignments belong in:

`assignment_history`

Never use `assigned_to` as assignment history.

---

## Complaint Relationships

Use:

`complaint_relations`

for relationships between complaints.

Use:

`duplicate_groups`

for duplicate grouping.

Do not overload complaint fields to represent relationships.

---

## SLA

SLA rules must be configurable.

Use:

`sla_policies`

for configuration.

Use:

`sla_audit`

for SLA events and breaches.

Do not hardcode SLA values throughout the application.

---

## Notifications

Use:

`notification_outbox`

for notification events.

Do not tightly couple complaint logic to push notification providers.

MVP may use in-app notifications.

---

## Geography

Solapur geography must come from real supplied data.

Important entities:

- 8 zones
- 26 election wards
- 98 census wards

Do NOT fabricate ward polygons or coordinates.

Use PostGIS for geographic operations.

---

## AI

AI services must be replaceable.

Use service interfaces for:

- Classification
- Duplicate Detection
- Trend Detection
- Resolution Verification
- Assistant

The core system must work without advanced AI.

---

## MVP AI

Initial classification may use:

- deterministic rules
- keywords
- mock classifier

Do not claim that a trained model exists unless it actually exists.

Duplicate detection MVP can use:

- text similarity
- GPS proximity
- time proximity
- category similarity

Advanced semantic embeddings can be added later.

---

## Resolution Verification

Do NOT use SSIM as the sole resolution signal.

MVP verification should combine:

- before image
- after image
- GPS
- timestamp
- citizen confirmation

---

## Feature Flags

Advanced capabilities should be replaceable using feature flags.

Examples:

VISION_AI_ENABLED
RAG_ENABLED
ADVANCED_VERIFICATION
PUSH_NOTIFICATIONS

Disabled advanced features must not break the core application.

---

## Backend Architecture

Prefer a modular monolith for the MVP.

Do not introduce microservices unless explicitly requested.

Business logic belongs primarily in the backend.

Do not duplicate important business rules across:

- Mobile
- Web
- Backend

---

## Database

Use migrations.

Never silently modify the schema without a migration.

Use:

- foreign keys
- constraints
- indexes
- transactions where appropriate

Use PostGIS for geospatial operations.

---

## Security

Never:

- hardcode secrets
- commit API keys
- trust client-side authorization
- expose sensitive internal errors
- blindly trust uploaded filenames
- accept arbitrary upload types

Validate all API inputs and uploads.

---

## Implementation Philosophy

Build vertically.

Prefer:

small change
→ test
→ implement
→ verify
→ integrate

Do not build huge disconnected modules.

---

## Before Coding 

Before implementing a feature:

1. Read relevant project documentation.
2. Inspect existing code.
3. Identify affected layers.
4. Create a small implementation plan.
5. Implement the smallest reasonable slice.
6. Add/update tests.
7. Run tests.
8. Review the diff.

---

## Critical Rule

Never sacrifice the working complaint lifecycle for advanced AI functionality.

A simple working municipal workflow is more important than an impressive but broken AI demo.