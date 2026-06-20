# Clinical Safety

This document describes the safety mechanisms built into OphthalmoAI: how the system decides a result needs human review, how clinicians can override or correct an AI result, how urgent findings are escalated, and what to do if something goes wrong. It is meant to be read alongside `docs/INTENDED_USE.md` (what the system is for) and `docs/CLINICAL_VALIDATION.md` (how well it performs).

## 1. Layered Safety Design

No single mechanism here is treated as sufficient on its own. The system layers four independent safety mechanisms, on the assumption that any one of them can fail or be misconfigured without the whole system failing silently:

1. **Image Quality Assessment** (`backend/iqa.py`) — catches bad inputs before they produce a confident-sounding wrong answer.
2. **Calibrated confidence + uncertainty estimation** (`backend/calibration.py`, `backend/uncertainty.py`) — makes the model's stated confidence trustworthy, and flags cases where the model is internally inconsistent across repeated stochastic passes.
3. **Clinical coding and urgency triage** (`backend/clinical_codes.py`) — every diagnosis carries a fixed urgency tier independent of model confidence, so a confidently-wrong "Cataract" prediction on an actual Uveitis case is still bounded by symptom cross-checking (layer 4) rather than relying on the model alone to know it's wrong.
4. **Symptom cross-check engine** (`backend/main.py: analyze_symptoms`) — flags mismatches between the AI's visual diagnosis and patient-reported symptoms, independent of the model's confidence in its own visual read.

## 2. Human Review Policy

### 2.1 When a result is auto-flagged

`backend/uncertainty.py: needs_human_review()` flags a result whenever any of the following is true:

| Condition | Threshold | Rationale |
|---|---|---|
| Confidence below threshold | < 75% (default) | Below this, the model itself is signaling low certainty |
| Epistemic uncertainty above threshold | MC-Dropout variance > 0.15 (default) | The model is inconsistent with itself across repeated stochastic passes — a sign the input sits near a decision boundary |
| Diagnosis is sight-threatening/systemic-emergency AND confidence below stricter threshold | Uveitis or Jaundice, confidence < 90% | The cost of a missed or wrong call on these specific conditions is categorically higher than for the others in the taxonomy |

These thresholds are configurable (`DEFAULT_CONFIDENCE_THRESHOLD`, `DEFAULT_UNCERTAINTY_THRESHOLD`, `CRITICAL_CONFIDENCE_THRESHOLD` in `backend/uncertainty.py`) and should be tuned against real validation data (see `docs/CLINICAL_VALIDATION.md`) rather than left at their illustrative defaults in any real deployment.

### 2.2 What "flagged for review" means operationally

A `requires_human_review: true` response is not a soft suggestion — it is a signal that the deploying system **must** route this result to a qualified human reviewer before it is presented to a patient as actionable, or before any downstream action (referral, scheduling, treatment) is triggered automatically. How that routing happens (a clinician queue, a required confirmation step in a UI, etc.) is the responsibility of the deploying organization; this codebase provides the signal and the override-recording mechanism, not a complete clinical workflow product.

### 2.3 Image quality and review

A result built from an image that failed IQA checks (`iqa_acceptable: false`) should be treated with the same caution as a low-confidence result, even if the model's stated confidence happens to be high — a confident answer on a bad input is not more trustworthy than an uncertain one.

## 3. Escalation for Urgent and Emergency Findings

Every diagnosis carries a fixed urgency tier from `backend/clinical_codes.py`, independent of model confidence:

| Diagnosis | Urgency | Escalation behavior |
|---|---|---|
| Jaundice (scleral icterus) | **Emergency** | `escalation_message` directs to same-day internal medicine/gastroenterology evaluation — this is flagged as a systemic, not ophthalmic, emergency |
| Uveitis | **Urgent** | `escalation_message` directs to same-day-if-symptomatic ophthalmologist/uveitis specialist evaluation |
| Conjunctivitis, Eyelid | Non-urgent | Routine GP/optometrist referral |
| Cataract, Pterygium | Elective | Routine ophthalmologist referral for monitoring/surgical evaluation timeline |
| Normal | None | Routine screening interval |

The `escalation_message` field is non-null only for urgent/emergency tiers, by design — its presence in a response is itself a signal the UI layer can branch on without needing to separately parse the urgency string. Frontend implementations should treat a non-null `escalation_message` as something to surface prominently, not bury in collapsed detail text.

**This urgency tier is independent of the AI's diagnosis confidence.** A 40%-confidence Uveitis prediction still carries the urgent escalation message — the system does not suppress urgency information just because the underlying diagnosis is uncertain. Uncertainty about *which* condition this is does not reduce the cost of missing a sight-threatening one if it's in the differential.

## 4. Clinician Override Mechanism

Any user with the `clinician` or `admin` role can record a structured second opinion on any scan via `POST /scans/{scan_id}/override`:

- **`agree`** — confirms the AI result.
- **`disagree`** — requires a `corrected_diagnosis`; records what the clinician believes the actual finding to be.
- **`inconclusive`** — the clinician could not determine a diagnosis from the available information (this is itself useful signal, distinct from agreement or disagreement).
- **`insufficient_image_quality`** — the clinician judges the image itself inadequate for any diagnostic conclusion, independent of what the model said.

Each scan can have at most one override recorded (enforced at the database level — `clinician_overrides.scan_id` is unique). This is append-only data: overrides are never edited or deleted, only added, which preserves a clean audit trail of what was actually reviewed and when. See `docs/CLINICAL_VALIDATION.md` Section 4 for how this data should be used as an ongoing performance-monitoring signal.

## 5. Audit Trail

Every prediction, chat interaction, login, registration, and clinician override is logged to the `audit_logs` table (`backend/audit.py`) with a timestamp, the acting user (if authenticated), the action type, success/failure, and relevant metadata. This trail is:

- **Append-only.** Rows are never updated or deleted by application code.
- **Best-effort relative to the primary operation.** A failure to write an audit log entry is itself logged but never blocks or fails the user-facing request — the audit system is not allowed to become a new point of failure for patient-facing functionality. This is a deliberate tradeoff: it means the audit trail is not a hard guarantee in the case of a database outage during the exact moment of a request. Deployments with stricter compliance requirements (e.g., requiring a complete audit trail with no gaps) should consider making audit writes synchronous and blocking, which this codebase does not do by default.

Admins can query the trail via `GET /admin/audit-logs`.

## 6. Model Versioning and Rollback

Every trained model checkpoint that's registered (`backend/model_registry.py`) carries its validation metrics and calibration temperature alongside the weights path. Promoting a new model to active, or rolling back to a previous version, is recorded with a timestamp and the admin who performed the action.

**Important operational caveat:** activating a model version in the registry (`POST /admin/model-registry/activate`) updates the database record of which version *should* be active — it does not hot-swap the weights currently loaded in a running API process's memory. A process restart (or a future hot-reload mechanism, not yet implemented) is required for a registry change to actually affect inference. Treat registry activation as "staging the next deployment," not as an instantaneous production change. Document this clearly in your deployment runbook, and use a blue/green or canary rollout process for any model update rather than activating-and-hoping.

## 7. What This System Does Not Do

To avoid creating false confidence in the safety net:

- It does not detect or prevent adversarial or deliberately misleading image uploads.
- It does not validate that the uploaded image is actually of a real human eye versus, e.g., a stock photo or another person's eye submitted on someone else's behalf — IQA checks for iris/pupil-like circular structures, which is a much weaker check than identity or liveness verification, and was not designed to be one.
- It does not currently support a structured user-facing "report a wrong diagnosis" feedback path outside the clinician-override mechanism (which requires a clinician account) — a patient-facing feedback or appeals path is a gap, not a built feature, as of this writing.
- It does not perform real-time monitoring or alerting on drift, degraded subgroup performance, or anomalous prediction-distribution shifts in production. The audit log and clinician-override tables provide the raw data such monitoring would need, but the monitoring itself is not implemented.

## 8. Incident Response

If a safety-relevant issue is identified in production (e.g., a pattern of clinician disagreement on a specific condition, a discovered subgroup performance gap, an IQA bypass):

1. Query the audit log and override tables for the affected scope (diagnosis, time range, or affected user cohort) to characterize the issue.
2. If the issue affects an active model version's reliability, use `backend/model_registry.py: rollback()` to revert to the previous version, then restart the API process to apply it (see Section 6 caveat).
3. Document the incident, root cause, and remediation — this codebase does not currently include a formal incident log template; deploying organizations should adopt one appropriate to their regulatory context.

This document should be reviewed any time a new safety mechanism is added or an existing threshold is changed.
