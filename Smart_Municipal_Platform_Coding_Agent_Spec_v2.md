# Smart Municipal Complaint & Resolution Intelligence Platform
## Coding Agent Specification — Solapur Hackathon MVP

> **Implementation contract:** Build the reliable complaint lifecycle first. Add intelligence features as replaceable layers on top of that lifecycle. Do not attempt to fully implement every advanced feature before the core workflow works end-to-end.

---

# 1. Product Goal

Build a Smart Municipal Complaint & Resolution Intelligence Platform for Solapur, Maharashtra.

The platform has **exactly two applications**:

1. **Mobile App — Citizen + Field Worker**
   - One React Native/Expo codebase
   - Role-based navigation

2. **Web App — Municipal Management**
   - One Next.js/React codebase
   - Combines Command Center/Admin + Department/Operations workflows
   - Role-based access and department filtering

The core complaint lifecycle is:

```text
Submitted
    ↓
Under Review
    ↓
Assigned
    ↓
In Progress
    ↓
Resolution Submitted
    ↓
Verified
    ↓
Closed
```

The product is an **intelligence and accountability platform**, not just a complaint logging application.

---

# 2. Implementation Priority

## MUST SHIP — Core MVP

Build these first and make them reliable:

- Authentication
- JWT + RBAC
- 26 Solapur wards seed data
- 8 Solapur zones seed data
- Departments seed data
- Citizen complaint creation
- Photo upload
- GPS capture
- PostGIS ward lookup
- Complaint status machine
- Officer review
- Field worker assignment
- Field worker task workflow
- Worker notes
- Support requests
- Rule-based severity
- Rule-based priority
- Simple duplicate grouping
- Assignment/reassignment history
- Configurable SLA policies
- SLA background job
- SLA reminders/escalations
- Command Center KPIs
- Complaint map pins
- Complaint detail page
- Audit logging
- In-app notification list

## STUB / MVP PLACEHOLDERS

These must have clean service interfaces, but do not require production-grade AI:

- Trained image classification
- Full RAG
- Advanced computer-vision resolution verification
- Push notifications

Use deterministic/demo implementations for these.

## LATER / STRETCH

Do not block the MVP for:

- Full MobileNetV3 training
- Advanced semantic duplicate models
- Sophisticated root-cause models
- Advanced resource optimization
- Predictive SLA failure
- Automatic worker assignment
- Offline worker mode
- Advanced public map functionality
- Production-scale deployment

---

# 3. Critical Rule for the Coding Agent

**Do not build eight independent feature projects.**

Build one reliable complaint lifecycle and attach intelligence services to it.

```text
Complaint Lifecycle
       │
       ├── AI Classification
       ├── Duplicate Detection
       ├── Trend Detection
       ├── Priority
       ├── SLA
       ├── Verification
       └── GenAI
```

Every intelligence feature must consume or enrich the same complaint/assignment data.

---

# 4. Architecture

```text
                         ┌──────────────────────────┐
                         │       MOBILE APP         │
                         │   React Native + Expo    │
                         │                          │
                         │  Citizen + Field Worker  │
                         └────────────┬─────────────┘
                                      │
                                      │ REST API
                                      ▼
                  ┌─────────────────────────────────────┐
                  │             FASTAPI                  │
                  │          Backend API                 │
                  │                                     │
                  │ Auth / RBAC                          │
                  │ Complaints                           │
                  │ Assignments                          │
                  │ SLA Engine                           │
                  │ Geo                                  │
                  │ Analytics                            │
                  │ AI Services                          │
                  │ Notifications                        │
                  │ Assistant                            │
                  │ Audit                                │
                  └───────────────┬─────────────────────┘
                                  │
             ┌────────────────────┼─────────────────────┐
             │                    │                     │
             ▼                    ▼                     ▼
     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
     │ PostgreSQL   │     │ AI Services  │     │ File Storage │
     │              │     │              │     │              │
     │ PostGIS      │     │ Classification│    │ Cloudinary   │
     │ pgvector     │     │ Duplicates   │     │ / Object     │
     │              │     │ Trends       │     │ Storage      │
     └──────────────┘     │ Verification │     └──────────────┘
                          │ Assistant    │
                          └──────────────┘


                         ┌──────────────────────────┐
                         │        WEB APP           │
                         │     Next.js + React      │
                         │                          │
                         │  Municipal Management    │
                         │                          │
                         │ Admin + Department       │
                         │ Command Center + Ops     │
                         └────────────┬─────────────┘
                                      │
                                      │ REST API
                                      ▼
                                  FastAPI
```

---

# 5. Repository Structure

Use a monorepo or equivalent structure:

```text
project/
├── apps/
│   ├── mobile/
│   │   ├── app/
│   │   ├── src/
│   │   └── ...
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── complaints/
│   │   ├── assignments/
│   │   ├── sla/
│   │   ├── geo/
│   │   ├── analytics/
│   │   ├── ai/
│   │   │   ├── classification/
│   │   │   ├── duplicates/
│   │   │   ├── trends/
│   │   │   └── verification/
│   │   ├── notifications/
│   │   ├── assistant/
│   │   └── audit/
│   │
│   ├── migrations/
│   ├── seeds/
│   └── tests/
│
├── database/
│   └── geo/
│       └── wards.geojson       # REQUIRED INPUT
│
├── docs/
└── README.md
```

Keep AI services behind interfaces so implementations can be replaced later.

---

# 6. Technology Stack

## Mobile

- React Native
- Expo
- TypeScript
- Expo Camera
- Expo Location
- React Navigation / Expo Router

## Web

- Next.js
- React
- TypeScript
- Tailwind CSS
- Leaflet / React Leaflet

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy

## Database

- PostgreSQL
- PostGIS
- pgvector

## Authentication

- JWT
- Password hashing
- Role-based authorization

## Storage

- Cloudinary or equivalent object storage

## AI

For MVP:

- Image classification → mock/keyword implementation
- Severity → transparent rules
- Department → category mapping
- Duplicate detection → text similarity + GPS + time
- Trend detection → simple statistical calculation
- Verification → GPS + timestamp + citizen confirmation
- Assistant → SQL-based answers to limited supported questions

Advanced implementations can replace these later without changing the core complaint APIs.

---

# 7. User Roles

## Citizen

Can:

- Register/login
- Submit complaints
- Upload/take photos
- Share GPS
- Track own complaints
- View related complaints
- View public complaint locations where allowed
- Receive in-app notifications
- Confirm/reject resolution

## Field Worker

Can:

- View assigned tasks
- View complaint location
- Navigate to location
- Accept assignment
- Update status
- Add worker notes
- Request additional support
- Upload progress photo
- Upload resolution photo
- Submit resolution

## Officer

Can:

- View department complaints
- Review complaints
- Review AI suggestions
- Edit category/severity
- Assign workers
- Reassign workers
- Merge duplicate groups
- Escalate
- Review resolution
- View department analytics
- Use supported assistant queries

## Department Head

Same web application as Officer, with broader department authority.

## Admin / Municipal Administrator

Can:

- View city-wide complaints
- View all departments
- View all wards/zones
- View command center KPIs
- View map
- View emerging alerts
- Manage assignments
- View SLA violations
- View workloads
- View audit logs
- Use assistant
- Override authorized workflow decisions

---

# 8. Role-Based Architecture

Do not create separate applications for each role.

## Mobile

```text
Login
  ↓
Role
  ├── citizen → Citizen navigation
  └── field_worker → Worker navigation
```

## Web

```text
Login
  ↓
Role
  ├── admin → Full Command Center
  ├── department_head → Department + broader controls
  └── officer → Department Operations
```

Backend must enforce permissions independently of the frontend.

Never trust role or department information sent by the client.

---

# 9. Database Schema

## users

```text
id
name
email
phone
password_hash
role
department_id
zone_id
created_at
updated_at
```

Roles:

```text
citizen
field_worker
officer
department_head
admin
```

---

## wards

```text
id
ward_name
zone_id
population
sc_population
st_population
boundary_geojson
```

Solapur seed:

- 26 election wards
- Real ward names/population data supplied by the project specification

Do not fabricate ward boundary polygons.

---

## zones

```text
id
zone_name
jurisdiction_description
```

Seed 8 Solapur zones.

---

## departments

```text
id
name
description
```

Departments:

```text
Solid Waste Management
Public Health & Sanitation
Roads & Infrastructure
Street Lighting
Water Supply
Urban Planning
Public Works
```

---

# 10. Complaints Table

```text
complaints
-----------
id
citizen_id
title
description

category
category_confidence

severity
severity_confidence
severity_reason

priority_score
priority_label
priority_reasons

ward_id
zone_id
location_lat
location_lng

assigned_department_id
assigned_to

status

sla_deadline

created_at
updated_at
assigned_at
resolved_at
closed_at
escalated_at
```

Categories:

```text
pothole
garbage
drainage
streetlight
water_leakage
other
```

Statuses:

```text
submitted
under_review
assigned
in_progress
resolution_submitted
verified
closed
rejected
reopened
```

---

# 11. Images

```text
images
------
id
complaint_id
url
image_type
created_by
created_at
```

Image types:

```text
before
progress
after
```

Optional verification metadata:

```text
verification_score
verification_result
```

Do NOT make SSIM the source of truth.

---

# 12. Assignment History

Do not use `assigned_to` as assignment history.

`complaints.assigned_to` represents the **current worker**.

Create:

```text
assignment_history
------------------
id
complaint_id
assigned_by
assigned_to
department_id
assigned_at
unassigned_at
reason
```

This preserves every assignment and reassignment.

---

# 13. Worker Notes

Create:

```text
worker_notes
------------
id
complaint_id
worker_id
note
created_at
```

Examples:

```text
Arrived at site.
Issue is larger than expected.
Need additional support.
Materials required.
Work completed.
```

---

# 14. Support Requests

Create:

```text
support_requests
----------------
id
complaint_id
requested_by
description
status
resolved_by
created_at
resolved_at
```

Statuses:

```text
requested
approved
rejected
fulfilled
```

---

# 15. Complaint Relationships

Do not overload `related_complaint_group_id`.

Use:

```text
complaint_relations
-------------------
id
complaint_id
related_complaint_id
relation_type
similarity_score
distance_meters
created_at
```

Relation types:

```text
possible_duplicate
duplicate
related
merged
```

A merged complaint must preserve the original citizen complaints.

---

# 16. Duplicate Groups

```text
duplicate_groups
----------------
id
ward_id
created_by
created_at
merged_into_complaint_id
```

The group references relationships rather than replacing original complaints.

---

# 17. Notification Outbox

Create:

```text
notification_outbox
-------------------
id
user_id
type
title
message
payload
channel
status
created_at
sent_at
```

Channels:

```text
in_app
push
```

For MVP, implement `in_app`.

Push can use the same outbox later.

---

# 18. SLA Configuration

Do NOT hardcode SLA timings across the codebase.

Create:

```text
sla_policies
-----------
id
department_id
status
reminder_after_minutes
escalate_after_minutes
enabled
created_at
updated_at
```

Default demo policy:

### Submitted

```text
2h → reminder
4h → escalate
```

### Under Review

```text
4h → reminder
8h → escalate
```

### In Progress

```text
8h → worker reminder
24h → supervisor escalation
```

### Resolution

```text
48h → citizen nudge
```

These values must be configurable.

---

# 19. SLA Job

Implement a background scheduler/worker.

Every run:

```text
Find active complaints
        ↓
Load SLA policy
        ↓
Calculate elapsed time
        ↓
Check reminder threshold
        ↓
Check escalation threshold
        ↓
Create notification
        ↓
Create audit record
        ↓
Update SLA audit
```

Create:

```text
sla_audit
---------
id
complaint_id
sla_type
expected_time
actual_time
action_taken
timestamp
```

Never send duplicate reminders/escalations.

---

# 20. Audit Logs

Create:

```text
audit_logs
----------
id
user_id
action
complaint_id
old_status
new_status
metadata
timestamp
```

Log:

- Status changes
- Assignment
- Reassignment
- Duplicate merge
- Escalation
- Resolution submission
- Verification
- Officer overrides
- Reopening
- Rejection

Audit history should be append-only.

---

# 21. Ward Detection

Use PostGIS.

Flow:

```text
GPS coordinates
      ↓
PostGIS Point
      ↓
Spatial polygon lookup
      ↓
Ward
      ↓
Zone
```

Use a spatial query such as `ST_Within`.

Do not hardcode ward logic in frontend code.

---

# 22. IMPORTANT: Ward GeoJSON Dependency

The repository currently does not contain the required Solapur ward GeoJSON.

Therefore:

1. Create the PostGIS geometry schema.
2. Create the import process.
3. Create the lookup API.
4. Add a clear setup requirement for `database/geo/wards.geojson`.
5. Do not invent ward polygons.
6. Provide a development fallback only if explicitly marked as demo/dev mode.

Example setup:

```text
database/geo/wards.geojson
        ↓
import script
        ↓
wards.boundary_geojson
        ↓
PostGIS geometry
```

---

# 23. Complaint Submission API

Suggested endpoint:

```text
POST /api/v1/complaints
```

Input:

```text
title
description
photo
latitude
longitude
```

Backend flow:

```text
Validate request
      ↓
Store image
      ↓
Detect ward
      ↓
Run AI classification interface
      ↓
Calculate severity
      ↓
Suggest department
      ↓
Check duplicates
      ↓
Calculate priority
      ↓
Create complaint
      ↓
Create audit record
      ↓
Create notification
```

---

# 24. AI Classification — MVP Stub

Do NOT block the project on training a vision model.

Create an interface:

```python
class ComplaintClassifier:
    def classify(self, image, text) -> ClassificationResult:
        ...
```

MVP implementation:

- Use simple keyword/text heuristics.
- Return deterministic mock confidence values for demo purposes.
- Clearly mark these values as demo/synthetic.

Example:

```json
{
  "category": "garbage",
  "confidence": 0.92,
  "source": "demo_classifier"
}
```

Later implementation:

```text
ComplaintClassifier
        ↓
MobileNetV3 / equivalent model
```

Do not claim MobileNetV3 is trained until actual training data/model exists.

---

# 25. Severity — MVP

Use transparent rules.

Severity:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Example signals:

```text
danger
flooded
collapsed
accident
unsafe
blocked
contaminated
```

Store the reason.

Example:

```json
{
  "severity": "high",
  "reason": [
    "public health keyword detected",
    "complaint duration"
  ]
}
```

---

# 26. Department Suggestion

Use a deterministic category → department mapping for MVP.

Example:

```text
garbage → Solid Waste Management
drainage → Public Health & Sanitation
pothole → Roads & Infrastructure
streetlight → Street Lighting
water_leakage → Water Supply
```

Officers can override the suggestion.

---

# 27. Priority Scoring

Use an explainable rule-based score.

Example:

```text
Severity       40
Duration       20
Duplicates     15
Safety Risk    25
-------------------
Maximum       100
```

Return:

```json
{
  "priority_score": 100,
  "priority_label": "critical",
  "reasons": [
    "High severity",
    "4 days unresolved",
    "3 related complaints",
    "Public health risk"
  ]
}
```

Do not create an opaque ML priority model for the MVP.

---

# 28. Duplicate Detection — MVP

Use:

```text
Text similarity
      +
GPS distance
      +
Time proximity
      +
Category
```

The MVP can use TF-IDF/cosine similarity or another lightweight method.

Later replace it with semantic embeddings.

Example:

```text
Complaint A
"Huge pothole outside City Mall"

Complaint B
"Deep pothole near City Mall entrance"

Similarity: 82%
Distance: 35m
Category: same
Time: 2h

→ Possible duplicate
```

Important:

**Never automatically delete or close the second complaint.**

Flow:

```text
Possible duplicate
      ↓
Officer review
      ↓
Merge OR Keep Separate
```

Original citizen complaints must remain linked.

---

# 29. Emerging Alerts

This is a secondary intelligence feature.

Do not block core complaint functionality on it.

Use simple statistical analysis:

```text
Recent count
vs
historical baseline
```

Example:

```text
Ward 1
Garbage complaints

Current: 23
Baseline: 7

Increase: +240%

🚨 Emerging issue
```

Add minimum count thresholds to avoid noisy alerts.

Create:

```text
emerging_alerts
---------------
id
ward_id
category
spike_percentage
alert_level
description
created_at
resolved_at
```

---

# 30. Root Cause / Recommendation Stub

Do not build a complex causal ML system for MVP.

Create a service interface:

```text
RecommendationService
```

MVP can derive recommendations from known metrics.

Example:

```text
Garbage complaints ↑
+
Open complaints ↑
+
Workers unavailable
        ↓
Recommendation:
Deploy additional workers
```

Always label recommendations as suggestions.

Do not present inferred causes as verified facts.

---

# 31. Resolution Verification — MVP

Do NOT implement SSIM-only verification.

MVP verification:

```text
Before photo
      +
After photo
      +
GPS match
      +
Timestamp
      +
Citizen confirmation
```

Example:

```text
Location match: ✓
Timestamp valid: ✓
Resolution photo uploaded: ✓
Citizen confirmed: ✓

→ VERIFIED
```

The system should provide a recommendation, not make an irreversible automatic closure solely from computer vision.

Final closure requires:

```text
Citizen confirmation
OR
Authorized officer override
```

If the citizen rejects the resolution:

```text
verified/review
      ↓
reopened
```

---

# 32. Advanced Verification — Later

Create a replaceable interface:

```python
class ResolutionVerifier:
    def verify(self, before_image, after_image, metadata):
        ...
```

Future implementation can include:

- Visual similarity
- Object detection
- Semantic image comparison
- GPS
- Timestamp

SSIM may be used as one signal, but never as the only decision.

---

# 33. Field Worker Workflow

```text
Worker Login
     ↓
Task List
     ↓
Open Assignment
     ↓
View GPS / Navigate
     ↓
Accept
     ↓
Arrived
     ↓
In Progress
     ↓
Worker Note / Progress Photo
     ↓
Complete Work
     ↓
After Photo
     ↓
Submit Resolution
```

Worker should be able to request additional support.

---

# 34. Citizen Workflow

```text
Login
 ↓
Report Problem
 ↓
Take Photo
 ↓
Capture GPS
 ↓
Describe Problem
 ↓
AI Suggestion
 ↓
Submit
 ↓
Track Status
 ↓
Resolution Submitted
 ↓
Verify
 ├── Yes → Closed
 └── No  → Reopened
```

Citizen should see a simple status timeline.

---

# 35. Web Command Center

One web application.

## Admin view

Top KPIs:

```text
Critical Complaints
Overdue Complaints
Unassigned Complaints
Emerging Issues
Open Complaints
Resolution Rate
Average Resolution Time
```

Main sections:

```text
Emerging Issues
SLA Status
Department Workload
Complaint Map
Recent Critical Complaints
```

The dashboard should answer:

> **What needs attention right now?**

---

# 36. Department Operations

Department users see:

- Their department complaints
- Pending assignments
- Assigned workers
- SLA status
- Priority
- Duplicate groups
- Ward distribution
- Resolution status
- Workload

Admin sees city-wide data.

Do filtering/authorization at the backend.

---

# 37. Complaint Detail Page

Show:

```text
Complaint ID
Title
Description
Before Photo
Progress Photos
After Photo

Location
Ward
Zone

Category
AI Confidence
Severity
Severity Reason

Priority Score
Priority Reasons

Department
Assigned Worker

Duplicate / Related Complaints

SLA Timer
Status Timeline
Audit History

Resolution Verification
Citizen Confirmation
```

Officer actions:

```text
Edit
Assign
Reassign
Merge
Escalate
Reject
Verify
Close
Reopen
```

---

# 38. Map

MVP map must show complaint pins.

Filters:

```text
Category
Status
Severity
Ward
Department
```

Use Leaflet + OpenStreetMap.

The public citizen map is **not required for the MVP**.

If implemented later, expose only safe public information and never expose citizen PII.

---

# 39. GenAI Assistant — MVP Stub

Do not block the MVP on full RAG.

Create:

```text
AssistantService
```

MVP implementation:

```text
Natural-language question
      ↓
Recognize supported question
      ↓
Run safe SQL query
      ↓
Return structured answer
```

Support a small set of questions:

```text
What are the major unresolved problems in Ward 1?

Which department has the highest workload?

Which wards have the most complaints?

Why is this complaint high priority?

Generate today's operational summary.
```

Do not fabricate statistics.

Every answer must be generated from actual database values.

---

# 40. Future RAG Architecture

Later:

```text
Complaint Data
      ↓
Embeddings
      ↓
pgvector
      ↓
Retriever
      ↓
Relevant complaints/documents
      ↓
LLM
      ↓
Grounded response
```

The MVP assistant must use a replaceable provider so this can be added later.

---

# 41. Notifications — MVP

Implement only an in-app notification center.

Events:

```text
Complaint submitted
Complaint assigned
Worker assignment
Status changed
SLA reminder
SLA escalation
Resolution submitted
Verification requested
Complaint reopened
Complaint closed
Emerging alert
```

Use `notification_outbox`.

Push notifications can later consume the same outbox.

---

# 42. API Structure

Use:

```text
/api/v1/auth
/api/v1/users

/api/v1/complaints
/api/v1/complaints/{id}
/api/v1/complaints/{id}/assign
/api/v1/complaints/{id}/status
/api/v1/complaints/{id}/resolve
/api/v1/complaints/{id}/verify
/api/v1/complaints/{id}/reopen
/api/v1/complaints/{id}/merge

/api/v1/assignments
/api/v1/workers
/api/v1/support-requests

/api/v1/wards
/api/v1/zones
/api/v1/departments

/api/v1/analytics
/api/v1/emerging-alerts

/api/v1/sla
/api/v1/notifications

/api/v1/ai/classify
/api/v1/ai/duplicates
/api/v1/ai/verification

/api/v1/assistant

/api/v1/audit
```

FastAPI should expose OpenAPI documentation.

---

# 43. Security

Implement:

- JWT
- Password hashing
- RBAC
- Department-level authorization
- Input validation
- File validation
- Rate limiting where appropriate
- Secure image handling
- No citizen PII in public endpoints
- Audit logging

Backend authorization is mandatory.

Frontend route guards are not sufficient.

---

# 44. Configuration

Use environment variables/configuration.

Example:

```text
DATABASE_URL=
JWT_SECRET=
CLOUDINARY_URL=

VISION_AI_ENABLED=false
RAG_ENABLED=false
ADVANCED_VERIFICATION_ENABLED=false
PUSH_NOTIFICATIONS_ENABLED=false

DEFAULT_SLA_ENABLED=true
```

Never commit secrets.

AI implementations must be replaceable through configuration/service dependencies.

---

# 45. Seed Data

Seed:

```text
26 wards
8 zones
7 departments
Admin users
Department heads
Officers
Field workers
Citizens
Demo complaints
Demo duplicate groups
Demo emerging alerts
```

Operational complaint/user data should be explicitly marked synthetic/demo where applicable.

Do not represent synthetic workers or complaints as real government records.

---

# 46. Demo Scenario

Use one primary complaint through the entire lifecycle.

Example:

```text
Citizen:
"Garbage has not been collected for 4 days near Tuljapur Naka."
```

Demo:

```text
Photo
 ↓
Category: Garbage
 ↓
Severity: High
 ↓
Department: Solid Waste
 ↓
Ward: Ward 1
 ↓
Duplicate check
 ↓
Priority: Critical
 ↓
Officer review
 ↓
Worker assignment
 ↓
Worker starts task
 ↓
Progress photo
 ↓
After photo
 ↓
Citizen verification
 ↓
Closed
```

Then separately demonstrate:

1. Duplicate grouping
2. Command Center map/KPIs
3. SLA escalation
4. Emerging alert
5. Assistant query

---

# 47. Implementation Phases

## Phase 1 — Foundation

- Repository
- Database
- Migrations
- PostGIS
- Auth
- RBAC
- Seed wards/zones/departments
- Basic API structure

## Phase 2 — Core Complaint Lifecycle

- Citizen submission
- Photo upload
- GPS
- Ward detection
- Complaint status machine
- Citizen tracking
- Worker assignments
- Assignment history
- Worker notes
- Support requests
- Resolution submission
- Citizen confirmation

## Phase 3 — Core Municipal Management

- Unified web application
- Admin/department role filtering
- Complaint list
- Complaint detail
- Assignment UI
- Worker management
- Command Center KPIs
- Complaint map pins
- Audit logs
- In-app notifications

**At this point there must be a fully working end-to-end product.**

## Phase 4 — Intelligence Layer

Add to the existing complaint lifecycle:

- Severity rules
- Priority scoring
- Department suggestion
- Duplicate grouping
- Classification stub

## Phase 5 — Municipal Intelligence

- Emerging alerts
- Workload analytics
- Recommendation stub

## Phase 6 — Accountability

- Configurable SLA policies
- SLA background job
- Reminders
- Escalations
- SLA audit
- Resolution verification

## Phase 7 — Assistant

- SQL-based assistant
- Supported operational questions
- RAG-ready service interface

---

# 48. Definition of Done

## Core MVP

The following must work:

```text
Citizen logs in
→ submits photo + text + GPS
→ ward is detected
→ complaint is stored
→ officer sees complaint
→ officer assigns worker
→ worker sees assignment
→ worker updates status
→ worker uploads resolution photo
→ citizen receives verification request
→ citizen confirms/rejects
→ complaint closes/reopens
→ complete audit history exists
```

Additionally:

```text
26 wards seeded
8 zones seeded
PostGIS lookup works
Department filtering works
Map pins work
KPIs work
Assignment history works
SLA job works
In-app notifications work
```

Then intelligence layers must work against the same complaint:

```text
Severity
Priority
Duplicate grouping
Emerging alerts
Resolution verification
Assistant
```

---

# 49. Testing Requirements

At minimum test:

## Authentication
- Login
- Invalid credentials
- Role restrictions

## Complaint
- Create
- Read
- Update
- Status transitions
- Invalid transitions

## Authorization
- Citizen cannot access another citizen's private complaint
- Worker can only access assigned tasks
- Officer sees only authorized department data
- Admin sees all authorized data

## Geo
- Valid GPS → correct ward
- Invalid/outside coordinate handling

## Assignment
- Assign
- Reassign
- Assignment history

## Duplicate
- Possible duplicate detected
- Merge
- Keep separate
- Original complaints preserved

## SLA
- Reminder threshold
- Escalation threshold
- No duplicate notifications
- Audit entry

## Resolution
- Submit resolution
- Citizen confirms
- Citizen rejects → reopen

---

# 50. UI Principles

Keep interfaces simple and operational.

## Citizen

Primary action:

```text
REPORT A PROBLEM
```

Avoid complicated forms.

## Field Worker

Primary action:

```text
MY TASKS
```

Show:

```text
Priority
Location
Complaint
Required action
Status
```

## Officer

Primary action:

```text
WHAT NEEDS MY ATTENTION?
```

Show:

```text
Critical
Overdue
Unassigned
Emerging
```

## Admin

Primary action:

```text
WHAT IS HAPPENING ACROSS SOLAPUR?
```

Show:

```text
City KPIs
Map
Emerging Issues
Department Workload
SLA
```

---

# 51. Product Positioning

The product should feel like:

> **Municipal Intelligence + Accountability**

not:

> **A basic complaint management app.**

The system should answer:

```text
What is happening?
Where is it happening?
How serious is it?
Is it getting worse?
Are complaints duplicates?
Who should handle it?
Who is overloaded?
Is the SLA being missed?
Was the problem actually fixed?
What should the municipality do next?
```

---

# 52. Final Engineering Rule

**Do not sacrifice the working complaint lifecycle for advanced AI.**

If time is running out:

1. Finish the core lifecycle.
2. Finish the unified mobile app.
3. Finish the unified web app.
4. Finish database + PostGIS.
5. Finish assignment + SLA.
6. Then add AI demonstrations.

A polished, reliable lifecycle with intelligent layers is better than a collection of unfinished AI features.
