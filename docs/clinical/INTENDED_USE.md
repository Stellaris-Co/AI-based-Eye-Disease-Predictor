# Intended Use Statement

**Status: Draft — requires review and sign-off by a qualified clinician and regulatory advisor before any clinical deployment.**

This document defines what OphthalmoAI is designed to do, who it is designed for, and where its boundaries are. It exists so that everyone touching this system — engineers, clinicians, deployers, and patients — shares the same understanding of what a result from this system does and does not mean.

## 1. What OphthalmoAI Is

OphthalmoAI is a software screening aid that analyzes a photograph of a human eye and produces a probability distribution over a small set of visually-apparent ocular and adnexal conditions (cataract, conjunctivitis, uveitis, eyelid conditions, pterygium, scleral icterus/jaundice, or no apparent abnormality), along with a confidence score, an uncertainty estimate, a Grad-CAM visual explanation, and triage-oriented metadata (suggested urgency, ICD-10/SNOMED-CT codes, and a recommendation for whether the result should be reviewed by a clinician before being acted on).

It is intended to function as a **decision-support and triage aid** — narrowing attention and prioritizing follow-up — not as a standalone diagnostic instrument.

## 2. What OphthalmoAI Is Not

OphthalmoAI is **not**:

- A medical device cleared or approved by the FDA, CE marking authority, or any other regulatory body, unless and until that approval has actually been obtained and is documented in this repository.
- A replacement for an eye examination performed by a qualified clinician using appropriate instrumentation (slit lamp, tonometry, fundoscopy, visual acuity testing, etc.).
- Capable of diagnosing conditions that are not visually apparent from an external photograph of the eye — it cannot measure intraocular pressure, assess the retina or optic nerve, or detect conditions whose only signs are functional (visual field loss, color vision deficits) rather than structural/visible.
- Validated for pediatric use, for non-human subjects, or for any condition outside the seven labels in its training taxonomy.
- A system that should be used to rule out a condition. A "Normal" result means the model did not detect visual signs of the conditions it was trained to recognize — it does not mean the eye is healthy in any broader sense.

## 3. Intended Users

- **Primary**: Triage staff, community health workers, or telehealth intake systems operating in settings where immediate access to an ophthalmologist is not available, using OphthalmoAI to help prioritize who needs urgent in-person evaluation.
- **Secondary**: Patients using the system for educational, screening-awareness purposes, with the explicit understanding (enforced via the UI's disclaimers) that any result requires follow-up with a real clinician.
- **Not intended for**: Use as the sole basis for a treatment decision, prescription, or surgical referral without clinician review, particularly for any result flagged `requires_human_review: true` or with `urgency` of `"urgent"` or `"emergency"` (see `backend/clinical_codes.py` and `backend/uncertainty.py`).

## 4. Operating Conditions and Limitations

- **Image quality dependency.** Performance is dependent on image quality (focus, lighting, framing). The system includes an Image Quality Assessment step (`backend/iqa.py`) that surfaces warnings for likely-unusable images, but does not guarantee that an image that passes IQA is clinically adequate.
- **Confidence is calibrated, not certain.** Confidence scores are passed through temperature scaling (see `docs/CLINICAL_VALIDATION.md`) to better reflect real-world accuracy, but a calibrated 90% confidence score still means the model is expected to be wrong roughly 1 in 10 times at that confidence level — calibration corrects systematic overconfidence, it does not eliminate error.
- **Dataset demographics are not fully characterized.** As of this writing, the training dataset's demographic composition (age, sex, ethnicity, skin tone, eye color, geographic origin, camera/device type) has not been formally documented or audited for representativeness. Performance may vary across these dimensions in ways that have not yet been measured. **This is a known gap, not a resolved item** — see Section 6.
- **Single-image, single-eye basis.** Each prediction is based on one photograph of one eye, with no temporal context (prior images, disease progression) and no contralateral-eye comparison.
- **Differential diagnosis is not exhaustive.** The seven-label taxonomy does not cover the full range of ophthalmic and systemic conditions that can present with similar external signs (e.g., glaucoma, corneal ulcers, scleritis, orbital cellulitis are not in scope and will not be correctly labeled if photographed).

## 5. Conditions Requiring Mandatory Human Review

The system is configured (see `backend/uncertainty.py`) to flag results for mandatory human clinician review when any of the following hold:
- Confidence is below 75% (default threshold, configurable via `DEFAULT_CONFIDENCE_THRESHOLD`).
- Estimated epistemic uncertainty (via Monte Carlo Dropout) exceeds the configured threshold.
- The diagnosis is Uveitis or Jaundice — both sight-threatening/systemic-emergency conditions — and confidence is below 90% (a stricter bar than the general case).
- The Image Quality Assessment step flags the input image as likely unusable.

Operators integrating this system into a clinical workflow must ensure that `requires_human_review: true` results are actually routed to a qualified reviewer before any action is taken, and must not present unreviewed urgent/emergency results to a patient as a final answer.

## 6. Known Gaps Requiring Resolution Before Clinical Deployment

This list is intentionally explicit rather than smoothed over, because pretending these are resolved would be more dangerous than naming them:

1. **No formal clinical validation study has been conducted.** `scripts/evaluate_models.py` produces per-class sensitivity/specificity/AUC against an internal holdout split, which is necessary but not sufficient — it is not a substitute for a prospective or externally-validated clinical study against a reference standard (ophthalmologist diagnosis).
2. **Dataset demographic and equity audit is outstanding.** See Section 4.
3. **No regulatory clearance has been sought or obtained** in any jurisdiction.
4. **No prospective real-world performance monitoring is in place** beyond the audit log and clinician-override mechanism (`backend/db.py: ClinicianOverride`), which depend on clinicians actually using the override feature consistently.
5. **The 7-condition taxonomy has not been clinically reviewed** for completeness or for whether the chosen groupings (e.g., bundling Conjunctivitis/Jaundice/Normal/Pterygium into one "Ocular Surface Disorders" specialist) reflect a defensible clinical decision boundary.

## 7. Revision Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-20 | Initial draft created alongside clinical-grade infrastructure build-out | Engineering |

This document should be reviewed and re-approved any time the model, taxonomy, or deployment context changes materially.
