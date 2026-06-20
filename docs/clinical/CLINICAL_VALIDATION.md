# Clinical Validation Report

**Status: Template — no validation run has been completed and signed off as of this writing. Every numeric placeholder below must be replaced with real, reproducible figures before this document can be cited as evidence of model performance.**

This document is the standard structure for reporting OphthalmoAI's measured performance. It is generated in two layers:

1. **Machine-readable layer**: `models/validation_report.json`, produced automatically by `scripts/evaluate_models.py`. This is the source of truth for the numbers below — never edit numbers in this file without re-running that script and confirming the regenerated JSON matches.
2. **Human-readable layer**: this document, which interprets the JSON output and adds the context a regulatory reviewer or clinical partner needs (validation set provenance, methodology, limitations) that the script cannot itself capture.

## 1. Methodology

### 1.1 Validation Set Construction

*(To be completed: describe how the holdout/validation split was created. At minimum, document:)*
- Total number of images per class.
- Whether the split was patient-level (no image from the same patient/eye appears in both train and validation) or image-level. **Patient-level splitting is required for a credible validation claim** — image-level splitting on images from the same eye/session can produce inflated performance estimates due to data leakage.
- Source of the validation images (same distribution as training data, or a held-out external dataset — these support very different strength of claim).
- Date range and collection method/device(s).

### 1.2 Calibration

Confidence scores are calibrated via temperature scaling (Guo et al., 2017) before being reported, using `scripts/calibrate_models.py`. The calibration temperature for each specialist model is recorded in `models/calibration.json` and surfaced in every `/predict` response as `calibration_temperature` and `calibrated: true/false`.

### 1.3 Metrics Reported

For each class within each specialist model group, `scripts/evaluate_models.py` computes:
- **Sensitivity** (true positive rate): of all images truly belonging to this class, what fraction did the model correctly identify.
- **Specificity** (true negative rate): of all images not belonging to this class, what fraction did the model correctly exclude.
- **AUC** (area under the ROC curve, one-vs-rest): a threshold-independent measure of discriminative ability.
- **Expected Calibration Error (ECE)**: the average absolute gap between the model's stated confidence and its actual accuracy at that confidence level, in 10 equal-width bins. Lower is better; 0.0 is perfect calibration.

## 2. Results

*(To be populated from `models/validation_report.json` after running `scripts/evaluate_models.py` against a finalized validation set. Example structure shown below with placeholder values — replace entirely with real output.)*

### 2.1 Router (Anatomical Group Classification)

| Metric | Value |
|---|---|
| Overall accuracy | *pending* |
| Validation set size | *pending* |

### 2.2 Anterior Segment Specialist (Cataract vs. Uveitis)

| Class | Sensitivity | Specificity | AUC | n |
|---|---|---|---|---|
| Cataract | *pending* | *pending* | *pending* | *pending* |
| Uveitis | *pending* | *pending* | *pending* | *pending* |

**Expected Calibration Error**: *pending*
**Calibration temperature applied**: *pending*

### 2.3 Ocular Surface Specialist (Conjunctivitis / Jaundice / Normal / Pterygium)

| Class | Sensitivity | Specificity | AUC | n |
|---|---|---|---|---|
| Conjunctivitis | *pending* | *pending* | *pending* | *pending* |
| Jaundice | *pending* | *pending* | *pending* | *pending* |
| Normal | *pending* | *pending* | *pending* | *pending* |
| Pterygium | *pending* | *pending* | *pending* | *pending* |

**Expected Calibration Error**: *pending*
**Calibration temperature applied**: *pending*

## 3. Subgroup Performance

*(To be completed once dataset demographics are characterized — see `docs/INTENDED_USE.md` Section 6, item 2. Performance should be broken out by any demographic or technical dimension where the dataset has adequate representation to support a subgroup estimate — e.g., by skin tone category, by age band, by capture device, by lighting condition. Do not report a subgroup metric computed on fewer than ~30 samples; state the gap instead.)*

## 4. Clinician Agreement (Post-Deployment)

Once deployed with the clinician override feature active (`ClinicianOverride` table, `POST /scans/{id}/override`), agreement rate between the model's top prediction and clinician verdict should be tracked over time as a post-market surveillance signal, separate from and complementary to the pre-deployment validation above. Query pattern:

```sql
SELECT
  sr.diagnosis AS model_diagnosis,
  co.verdict,
  co.corrected_diagnosis,
  COUNT(*) AS n
FROM scan_results sr
JOIN clinician_overrides co ON co.scan_id = sr.id
GROUP BY sr.diagnosis, co.verdict, co.corrected_diagnosis
ORDER BY n DESC;
```

A sustained disagreement rate above whatever threshold the deploying clinical team considers acceptable should trigger a model review, not just be logged and left unreviewed.

## 5. Limitations of This Validation

- Performance figures in this document reflect held-out internal validation data only, unless explicitly marked otherwise. They are not a substitute for prospective external validation.
- AUC, sensitivity, and specificity are reported per-class in a one-vs-rest framing; they do not capture confusion patterns *between* the non-reference classes, which the full confusion matrix (also in `validation_report.json`) does.
- No statistical confidence intervals are currently computed around these point estimates. For small validation sets, point estimates alone overstate precision — bootstrap confidence intervals should be added before this document is used to support any clinical or regulatory claim.

## 6. Sign-off

| Role | Name | Date | Notes |
|---|---|---|---|
| Model validation reviewer | *pending* | | |
| Clinical reviewer | *pending* | | |
| Regulatory/compliance reviewer | *pending* | | |

This document must not be cited externally as evidence of clinical performance until this sign-off table is complete.
