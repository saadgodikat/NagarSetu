---
description: NagarIQ-specific web dashboard UI and UX requirements
globs:
  - "apps/web/**/*"
alwaysApply: false
---

# NagarIQ Web UI Rules

## Product Identity

NagarIQ is a Municipal Intelligence & Accountability Platform.

The web application is an operational command center, not a generic analytics dashboard.

The UI should communicate:

- municipal operations
- accountability
- urgency
- geographic intelligence
- workload
- SLA performance
- complaint resolution

---

## Design Direction

Build a professional civic/government operations interface.

Avoid generic AI-generated dashboard aesthetics.

Avoid:

- excessive gradients
- excessive glassmorphism
- unnecessary glowing effects
- decorative animations
- meaningless charts
- oversized hero sections
- excessive rounded cards
- excessive color usage

Prefer:

- clear information hierarchy
- strong typography
- restrained visual language
- meaningful status indicators
- dense but readable operational information
- consistent spacing
- accessible contrast
- responsive layouts

---

## Command Center

The main dashboard should prioritize action.

Important information includes:

1. High-priority complaints
2. SLA breaches
3. Complaints requiring review
4. Unassigned complaints
5. Department workload
6. Active field operations
7. Geographic hotspots
8. Recent complaint trends

Do not prioritize decorative KPI cards over actionable information.

---

## Complaint Detail

A complaint detail page should make the complete lifecycle visible.

Show, where applicable:

- complaint ID
- category
- description
- submitted image
- location
- ward
- zone
- severity
- priority
- department
- current status
- current assignee
- SLA state
- assignment history
- worker notes
- support requests
- resolution evidence
- verification
- citizen confirmation
- audit history

---

## Status

Statuses must be visually distinguishable.

Do not rely on color alone.

Use:

- text labels
- icons where useful
- accessible contrast
- consistent status styling

---

## Maps

Maps should provide operational value.

Useful map information includes:

- complaint locations
- priority
- status
- ward
- zone
- hotspots

Do not add a map merely as decoration.

---

## Tables

Operational tables should support:

- search
- filtering
- sorting
- pagination where necessary

Frequently needed filters include:

- status
- priority
- department
- ward
- zone
- SLA state
- assignment state

---

## Loading States

Every data-driven view should handle:

- loading
- empty
- error
- success

Do not show a blank screen while data is loading.

---

## Responsive Design

The web application should remain usable on:

- desktop
- laptop
- tablet

Prioritize desktop because this is a municipal operations dashboard, but do not break smaller screens.

---

## Accessibility

Follow accessible UI practices.

Ensure:

- keyboard accessibility
- semantic HTML
- accessible labels
- sufficient contrast
- visible focus states
- meaningful error messages

Never rely only on color to communicate meaning.

---

## Components

Prefer reusable components.

Avoid giant page components.

Keep domain-specific business logic out of presentational components where possible.

---

## Data

The UI must consume backend APIs.

Do not fabricate production-looking municipal data in the application unless explicitly creating a demo fixture.

If demo data is required, clearly isolate it as seed/fixture data.

---

## AI Features

AI insights should be presented as decision support.

Do not make unsupported claims such as:

- "92% accurate"
- "100% verified"
- "AI guarantees resolution"

unless those metrics are actually measured and available.

---

## Demo Priority

The most important demo flow is:

Complaint
→ AI/rule classification
→ Priority
→ Ward
→ Department
→ Assignment
→ Worker action
→ Resolution evidence
→ Verification
→ Citizen confirmation
→ Closure

The UI should make this lifecycle easy to demonstrate.
