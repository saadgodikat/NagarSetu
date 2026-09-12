# NagarIQ – Phase 6: Multi-Signal Resolution Verification
## Accountability & Resolution Verification System

---

## 1. Objective

Provide an objective, automated, multi-signal resolution verification engine for municipal complaints in Solapur. 

When field workers report that civic issues (potholes, garbage dumps, drainage blockages, broken streetlights, water leakages) have been resolved, NagarIQ independently evaluates physical evidence, spatial proximity, chronological plausibility, and citizen satisfaction before closing complaints.

---

## 2. Architectural Rules & Philosophy

As mandated by **`Smart_Municipal_Platform_Coding_Agent_Spec_v2.md`** (Sections 31 & 32) and **`AGENTS.md`**:

1. **Strict Prohibition on SSIM-Only Verification**: Computer vision similarity algorithms (such as Structural Similarity Index - SSIM) alone are fragile in uncontrolled outdoor environments (variable lighting, weather, camera angle changes). SSIM must **never** be the sole decision maker.
2. **Multi-Signal Triangulation**: Resolution is verified by triangulating four independent signals:
   $$\text{Before/After Photo} + \text{GPS Match} + \text{Timestamp Validity} + \text{Citizen Confirmation}$$
3. **Non-Destructive Recommendations**: The system generates confidence scores and operational recommendations. Final closure strictly requires **citizen confirmation** or an **authorized officer override**. If a citizen rejects a resolution, the complaint automatically transitions to `reopened`.
4. **Anti-Fraud Safeguards**: The engine proactively flags copy-pasted or identical photos (`identical_photos_fraud_risk`) submitted to falsely claim task completion.

---

## 3. The 4 Verification Signals

| Signal | Dimension | Weight | Primary Rule | Pass / Score Criteria |
|---|---|---|---|---|
| **Signal 1: Photo Comparison** | Visual Evidence & Fraud Detection | **30%** | Visual change detected between before & after photos; identical photos flagged as fraud. | - $0.0$: Identical photo detected / missing after photo<br>- $0.70 - 1.0$: Genuine visual change indicating repair<br>- $0.60$: Single resolution photo (baseline absent) |
| **Signal 2: GPS Proximity** | Spatial Verification | **30%** | Resolution photo GPS must match complaint location within tolerance. | - $1.0$: $\le 150\text{m}$ (Exact match)<br>- $0.75$: $150\text{m} < d \le 300\text{m}$ (Acceptable drift)<br>- $0.40$: $300\text{m} < d \le 500\text{m}$ (Borderline warning)<br>- $0.0$: $> 500\text{m}$ (Out-of-bounds mismatch)<br>- $0.50$: Missing GPS (Neutral fallback) |
| **Signal 3: Timestamp Validity** | Turnaround & SLA Adherence | **15%** | Chronological sequence: $\text{resolved} \ge \text{assigned} \ge \text{created}$; checks plausible work duration. | - $1.0$: Valid & resolved within SLA<br>- $0.75$: Valid but resolved after SLA expired<br>- $0.40$: Suspiciously instantaneous ($< 30\text{s}$ turnaround)<br>- $0.0$: Clock anomaly ($\text{resolved} < \text{created}$) |
| **Signal 4: Citizen Feedback** | Citizen Confirmation & Rating | **25%** | Citizen confirmation status, star rating ($1-5$), and rejection reason. | - $1.0$: Confirmed with 5-star rating<br>- $0.60 - 0.90$: Confirmed with $2-4$ stars<br>- $0.60$: Pending citizen confirmation<br>- $0.0$: Rejected by citizen (Triggers reopening) |

---

## 4. Mathematical Scoring & Decision Synthesis

### Composite Verification Score Formula

$$\text{Score}_{\text{composite}} = \sum_{i=1}^{4} w_i \cdot s_i = 0.30 \cdot s_{\text{photo}} + 0.30 \cdot s_{\text{gps}} + 0.15 \cdot s_{\text{time}} + 0.25 \cdot s_{\text{citizen}}$$

### Decision Matrix

| Condition | Verification Status | Recommended Action |
|---|---|---|
| `identical_photos_fraud_risk` in flags | `rejected` | **FRAUD RISK**: Resolution photo is identical to the original report photo. Reject and initiate worker inquiry. |
| `citizen_rejected_resolution` in flags | `rejected` | **CITIZEN REJECTION**: Citizen rejected resolution. Complaint is automatically re-opened for further field work. |
| $\text{Score} \ge 0.75$ AND Citizen Confirmed | `verified` | **VERIFIED**: All verification signals passed and citizen confirmed. Ready for formal closure. |
| $\text{Score} \ge 0.75$ AND Citizen Pending | `provisionally_verified` | **PROVISIONALLY VERIFIED**: Photo, GPS, and timestamp verified. Awaiting citizen final confirmation. |
| $0.50 \le \text{Score} < 0.75$ OR warnings present | `requires_review` | **OFFICER REVIEW**: Requires operational officer review. Inspect physical evidence before approving. |
| $\text{Score} < 0.50$ | `rejected` | **REJECTED**: Verification failed multi-signal validation. Conflicting or insufficient evidence. |

---

## 5. Implementation Architecture

```text
               Worker Photo Upload / Operations Review / Citizen Decision
                                         │
                                         ▼
                             verify_complaint_resolution()
                          (app/ai/resolution_verifier.py)
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 │                       │                       │
                 ▼                       ▼                       ▼
      [MultiSignalVerifier]   [haversine_distance()]   [load_image_bytes()]
                 │
                 ▼
        VerificationResult
         - composite_score: float [0, 1]
         - status: verified | provisionally_verified | requires_review | rejected
         - signals: dict (photo, gps, timestamp, citizen breakdown)
         - recommendation: str (actionable guidance for officer)
         - flags: list[str] (e.g. identical_photos_fraud_risk, gps_location_mismatch)
                 │
                 ▼
      Persisted on Complaint:
      (verification_score, verification_status, verification_details, verified_at)
```

---

## 6. Database Schema & Migrations

Alembic migration `0003_resolution_verification.py` introduces:

### `complaints` Table:
- `verification_score`: `Float` (Composite score [0.0 - 1.0])
- `verification_status`: `String(32)` (Indexed for filtering: `verified`, `requires_review`, `rejected`, `provisionally_verified`)
- `verification_details`: `JSONB` (Complete dictionary of all 4 signal metrics, details, and flags)
- `verified_at`: `DateTime(timezone=True)`
- `citizen_rating`: `Integer` ($1 - 5$ star satisfaction rating)
- `citizen_feedback`: `Text` (Citizen review comments or rejection explanation)

### `images` Table:
- `latitude`: `Float` (Worker evidence capture latitude)
- `longitude`: `Float` (Worker evidence capture longitude)
- `captured_at`: `DateTime(timezone=True)`

---

## 7. API Surface

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/ai/verification` | Authenticated | Spec Section 42 endpoint: Run verification on-demand by complaint ID. |
| `GET` | `/api/v1/complaints/{id}/verification` | Citizen / Officer | Retrieve detailed multi-signal verification report with signal-by-signal breakdown. |
| `POST` | `/api/v1/complaints/{id}/verify` | Officer / Admin | Trigger on-demand re-evaluation of resolution verification. |
| `POST` | `/api/v1/worker/complaints/{id}/resolution-photo` | Field Worker | Upload resolution photo with optional `latitude` and `longitude` form fields; automatically triggers verification. |
| `POST` | `/api/v1/complaints/{id}/resolution/confirm` | Citizen | Confirm resolution with optional `rating` ($1-5$) and `feedback` text; updates citizen signal. |
| `POST` | `/api/v1/complaints/{id}/resolution/reject` | Citizen | Reject resolution with required reason; automatically re-opens complaint. |

---

## 8. Test Coverage

Comprehensive test suite in `backend/tests/test_resolution_verification.py` verifies **24 distinct test scenarios**:

1. **Photo Signal**:
   - `test_photo_signal_missing_after_photo`
   - `test_photo_signal_missing_before_photo`
   - `test_photo_signal_identical_photo_fraud_detection` (Fraud detection safeguard)
   - `test_photo_signal_valid_distinct_resolution_photos`
2. **GPS Proximity Signal**:
   - `test_haversine_distance_calculation`
   - `test_gps_signal_exact_location`
   - `test_gps_signal_close_vicinity`
   - `test_gps_signal_borderline_warning`
   - `test_gps_signal_out_of_bounds_mismatch`
   - `test_gps_signal_missing_coordinates`
3. **Timestamp Signal**:
   - `test_timestamp_signal_valid_within_sla`
   - `test_timestamp_signal_resolved_after_sla`
   - `test_timestamp_signal_clock_anomaly_negative`
   - `test_timestamp_signal_suspiciously_instantaneous`
4. **Citizen Feedback Signal**:
   - `test_citizen_signal_confirmed_with_5_stars`
   - `test_citizen_signal_confirmed_with_3_stars`
   - `test_citizen_signal_rejected`
   - `test_citizen_signal_pending`
5. **Composite Synthesis**:
   - `test_composite_verification_all_pass_citizen_confirmed`
   - `test_composite_verification_provisionally_verified_when_citizen_pending`
   - `test_composite_verification_blocks_on_identical_photo_fraud`
   - `test_composite_verification_citizen_rejection_overrides`
6. **Helper & Serialization**:
   - `test_verify_complaint_resolution_helper_stamps_complaint`
   - `test_factory_returns_singleton`

**Test Result**: 24/24 passed in 0.94s. Overall test suite (including SLA predictor and rule engine): 50/50 passed.
