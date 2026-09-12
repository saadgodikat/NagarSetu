---
description: React Native and Expo engineering rules for NagarIQ mobile application
globs:
  - "apps/mobile/**/*"
alwaysApply: false
---

# NagarIQ React Native + Expo Rules

## Application Architecture

NagarIQ has ONE mobile application.

The mobile application supports:

- CITIZEN
- FIELD_WORKER

Do not create separate mobile applications for these roles.

Use role-based navigation and permissions.

---

## Citizen Experience

Citizens should be able to:

- sign in
- create complaints
- enter complaint description
- capture/select a photo
- capture GPS location
- submit complaints
- view complaint status
- view complaint history
- receive in-app notifications
- view resolution evidence
- confirm or reject resolution

---

## Field Worker Experience

Field workers should be able to:

- sign in
- view assigned complaints
- inspect complaint details
- view complaint location
- view complaint photos
- update work status
- add worker notes
- request additional support
- capture resolution photos
- submit resolution evidence
- complete assigned work

---

## Role-Based Navigation

Navigation must be determined by the authenticated user's role.

Do not rely only on hiding UI elements.

The backend remains the authority for authorization.

The mobile client should gracefully handle HTTP 401/403 responses.

---

## Camera

When capturing complaint or resolution evidence:

- request camera permission only when needed
- handle permission denial
- handle camera errors
- provide a fallback where appropriate
- validate selected media

Do not assume camera access is always available.

---

## Location

Location is important to NagarIQ.

For complaint creation:

GPS
→ backend
→ PostGIS
→ ward
→ zone

The mobile application should capture location when appropriate.

Handle:

- permission denied
- location unavailable
- timeout
- inaccurate location
- device/location-service disabled

Do not fabricate coordinates.

---

## Image Uploads

Images should be uploaded through the backend API.

Handle:

- upload progress where useful
- network failure
- invalid image
- oversized image
- retry where appropriate

Do not expose storage credentials in the mobile application.

---

## API

The mobile application communicates with the FastAPI backend.

Do not duplicate backend business rules in the mobile application.

The backend determines:

- authorization
- complaint status transitions
- priority
- department
- ward/zone
- assignment
- SLA
- final verification state

---

## Authentication

Do not hardcode credentials or tokens.

Store authentication information using appropriate secure mobile storage mechanisms.

Handle:

- expired authentication
- logout
- unauthorized responses
- session restoration

---

## State Management

Use the simplest state management approach appropriate for the existing project.

Do not introduce a large state-management framework without inspecting the current architecture first.

Keep server state separate from local UI state where practical.

---

## Loading States

Every API-driven screen should handle:

- loading
- success
- empty
- error
- retry

Never leave users looking at a blank screen while an operation is pending.

---

## Network Failures

Network failures are expected.

For important operations:

- clearly show failure
- avoid silently losing user input
- allow retry where appropriate
- prevent accidental duplicate submissions

Do not claim offline support unless offline functionality has actually been implemented.

---

## Complaint Submission

The complaint flow should be:

Description
→ Photo
→ GPS
→ Submit
→ Backend processing
→ Ward/Zone
→ Classification
→ Priority
→ Department
→ Complaint created

The UI should communicate progress and result clearly.

---

## Resolution Submission

The worker flow should be:

Assigned complaint
→ Work started
→ Worker notes
→ Resolution photo
→ GPS/time evidence
→ Submit resolution
→ Verification
→ Citizen confirmation
→ Closure

Do not mark a complaint closed solely because the worker pressed "Complete."

---

## Accessibility

Use accessible:

- labels
- touch targets
- contrast
- error messages
- loading indicators

Do not rely only on color.

---

## Performance

Avoid unnecessary re-renders.

Use appropriate image sizing/compression.

Do not load large image assets unnecessarily.

Use list virtualization for potentially large complaint lists.

Do not prematurely optimize without evidence.

---

## Security

Never place:

- API secrets
- database credentials
- service-account credentials

inside the mobile bundle.

Treat all client-side data as potentially observable.

Backend authorization is mandatory.

---

## Demo Reliability

The primary demo flow must work reliably:

Citizen
→ Complaint
→ Photo/GPS
→ Ward
→ Officer
→ Assignment
→ Field Worker
→ Resolution Photo
→ Verification
→ Citizen Confirmation

Advanced AI features must not prevent this workflow from working.
