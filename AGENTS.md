# NagarIQ — AI Coding Agent Instructions

## Project

NagarIQ is a Municipal Intelligence & Accountability Platform for the Solapur municipal complaint workflow.

The authoritative project specification is:

`Smart_Municipal_Platform_Coding_Agent_Spec_v2.md`

Read it before implementing significant work.

## Architecture — MUST FOLLOW

NagarIQ has exactly two applications:

1. **Mobile — React Native + Expo**
   - Citizen role
   - Field Worker role
   - One mobile app with role-based navigation

2. **Web — Next.js**
   - Admin role
   - Department / Operations role
   - One web app with role-based access and filtering

Backend:

- FastAPI
- PostgreSQL
- PostGIS
- Alembic migrations
- Optional pgvector later

Use a modular monolith. Do not introduce microservices unless explicitly required.

## Core Complaint Lifecycle

The working lifecycle is:

Citizen submits complaint
→ AI/intelligence processing
→ department routing
→ prioritization
→ officer assignment
→ field worker assignment
→ work/resolution
→ resolution verification
→ citizen confirmation
→ closure

Build this lifecycle incrementally.

## Engineering Rules

- Inspect existing code before modifying it.
- Never rewrite working functionality unnecessarily.
- Prefer small vertical slices.
- Every significant feature must have explicit acceptance criteria.
- Add/update tests for behavior being introduced.
- Run relevant tests after implementation.
- Debug failures systematically; do not guess.
- Review the implementation before declaring completion.
- Do not stop at scaffolding when the requested feature is expected to work end-to-end.
- Do not introduce dependencies without a clear reason.
- Keep AI functionality behind replaceable interfaces.
- Use feature flags for unfinished/advanced AI capabilities.

## Data Integrity

- PostgreSQL/PostGIS is the source of truth.
- Use Alembic for schema changes.
- Never fabricate Solapur ward boundaries or geographic data.
- Preserve real ward/zone relationships.
- Use spatial queries and indexes appropriately.
- `complaints.assigned_to` represents the current assignee.
- Preserve reassignment history separately.
- Keep complaint relationships separate from duplicate groups.
- SLA configuration must not be hardcoded into application logic.

## AI

MVP AI may use deterministic/mock implementations where real models or training data are unavailable.

Do not pretend mocked AI is production ML.

Future capabilities such as semantic duplicate detection, advanced computer vision, and RAG should remain replaceable and isolated.

Resolution verification must NOT rely on SSIM alone.

## Security

- Backend owns authorization.
- Enforce RBAC server-side.
- Never trust role information supplied only by the client.
- Validate uploaded files and API input.
- Never commit secrets.
- Use environment variables for configuration.
- Do not expose internal credentials or sensitive information.

## UI

The product should look like a professional civic/operations platform, not a generic AI dashboard.

Prioritize:

- clear complaint lifecycle
- actionable dashboards
- useful filters
- accessible status indicators
- useful maps
- loading states
- empty states
- error states
- responsive layouts
- real API-backed data

Avoid decorative UI that does not help the municipal workflow.

## Implementation Strategy

Work in vertical slices:

L0 — Foundation
L1 — Citizen submission + complaint timeline
L2 — Officer triage
L3 — Assignment + SLA
L4 — Field worker resolution
L5 — Verification + citizen confirmation
L6 — Municipal intelligence / analytics
L7 — GenAI / RAG

Do not jump ahead unnecessarily.

The demo priority is a complete working complaint lifecycle, not the maximum number of AI features.

## Current State

L0 has been scaffolded.

Existing foundation includes:

- FastAPI backend
- JWT authentication
- RBAC helpers
- PostGIS models
- Alembic
- seed data
- Next.js login shell
- Expo login shell
- Solapur zones/wards/departments seed foundation

The database must be running before database-dependent integration testing.

## Before Each Significant Task

1. Read the relevant section of the project specification.
2. Inspect the existing implementation.
3. Identify what already works.
4. Define the smallest implementation slice.
5. Define acceptance criteria.
6. Implement incrementally.
7. Test.
8. Debug failures using evidence.
9. Review for security, data integrity, and architecture compliance.
10. Report what changed, what was tested, and what remains.

## Important

Do not invent requirements.

If the specification is ambiguous, inspect the existing architecture and state the ambiguity before making a consequential architectural decision.

Prefer a smaller working implementation over a larger incomplete one.

## Universal Agent Skills

Project-specific and engineering skills are stored under:

`.agent/skills/`

Before implementing a significant task, identify and read the applicable `SKILL.md` files.

### Skill selection

- New project/major feature/specification → `spec-driven-development`
- Breaking a feature into tasks → `planning-and-task-breakdown`
- Implementing a feature incrementally → `incremental-implementation`
- Tests/new behavior → `test-driven-development`
- Backend API design → `api-and-interface-design`
- PostgreSQL/PostGIS/database work → `postgis-database`
- React/Next.js web UI → `frontend-ui-engineering` and `nagariq-ui`
- React Native/Expo → `react-native-expo`
- Security/auth/uploads/RBAC → `security-and-hardening`
- Unexpected errors/test/build failures → `debugging-and-error-recovery`
- Browser UI/runtime verification → `browser-testing-with-devtools`
- Code quality/final review → `code-review-and-quality`

For a task involving multiple areas, read all applicable skills before implementation.

Do not blindly apply unrelated skills.

The skill files are instructional guidance, not executable programs. Follow their workflow while working on the relevant task.

## Agent Workflow

For significant work:

1. Read `AGENTS.md`.
2. Read the relevant section of `Smart_Municipal_Platform_Coding_Agent_Spec_v2.md`.
3. Identify applicable `.agent/skills/*/SKILL.md` files.
4. Read those skills before coding.
5. Inspect the existing implementation.
6. Create a small implementation plan.
7. Define acceptance criteria.
8. Implement incrementally.
9. Run tests.
10. Debug failures systematically.
11. Review the implementation.
12. Verify the actual runtime behavior where possible.
13. Report files changed, tests run, verification performed, and deferred work.

Never claim a feature works merely because the code was written.
