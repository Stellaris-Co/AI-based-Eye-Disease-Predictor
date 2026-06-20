# Product Notes
## OphthalmoAI

---

## 1. Summary

OphthalmoAI is a web app that screens user-uploaded eye photos for visible eye conditions. It returns a screening result, confidence score, Grad-CAM heatmap, symptom cross-check, care notes, and a chat helper for follow-up questions. The project is meant for learning, demos, and research, not for replacing an ophthalmologist.

---

## 2. Problem Statement

- Early detection of eye conditions dramatically improves patient outcomes, yet access to specialist ophthalmologists is limited in many regions.
- Patients frequently cannot interpret their own symptoms or know when a condition is urgent.
- Existing consumer-facing eye health tools are either overly simplistic or require proprietary hardware.

This project tries to help by providing:
- Screening from a standard photo upload
- Grad-CAM, treatment notes, and severity information in plain language
- A chat helper for follow-up eye-health questions

---

## 3. Goals

| Goal | Metric | Target |
|------|--------|--------|
| Accurate triage | Router model group accuracy | ≥90% on held-out data |
| Accurate diagnosis | Specialist model top-1 accuracy | ≥85% per class |
| Explainability | Grad-CAM coverage of diagnostically relevant region | Qualitative validation |
| Usability | Time from upload to result | <10 seconds on GPU |
| Accessibility | Correct display on mobile (375 px) | All core flows |
| Safety | Critical warnings shown for Uveitis, Jaundice | 100% of cases |

---

## 4. Expected Users

### Persona 1 — Concerned Patient (Primary)
- **Profile:** 35–65 year old, non-technical, has noticed a change in their eye appearance
- **Goal:** Understand what they are looking at and whether they should see a doctor urgently
- **Needs:** Simple upload, plain-English results, clear urgency signal, "Find a Doctor" CTA

### Persona 2 — Medical Student / Researcher
- **Profile:** Clinical student or AI/ML researcher exploring medical AI
- **Goal:** Understand the AI pipeline, explore Grad-CAM outputs, test model performance
- **Needs:** Confidence scores, probability distributions, heatmaps, technical documentation

### Persona 3 — Developer / Integrator
- **Profile:** Software engineer evaluating or extending the system
- **Goal:** Run the system locally, understand the API, contribute or deploy
- **Needs:** Docker support, API docs, clear code structure, environment variables

---

## 5. Features

### 5.1 Core Features

| ID | Feature | Priority |
|----|---------|----------|
| F01 | Upload eye scan (JPG/PNG/BMP) with built-in crop tool | P0 |
| F02 | Hierarchical AI inference (router + specialist) | P0 |
| F03 | Grad-CAM heatmap visualisation | P0 |
| F04 | Symptom cross-check (pain, vision, itch) | P0 |
| F05 | Clinical result card (diagnosis, confidence, severity, treatment) | P0 |
| F06 | 4-page PDF report generation | P1 |
| F07 | AI Doctor chatbot (Claude / Ollama) | P1 |
| F08 | Text-to-speech narration of results | P2 |
| F09 | "Find nearest ophthalmologist" Google Maps link | P2 |
| F10 | Conditions library (7 conditions with clinical detail) | P2 |
| F11 | Medical news / research feed | P3 |
| F12 | How It Works / pipeline explainer page | P3 |

### 5.2 Out of Scope (v1.0)

- User authentication / patient record persistence
- Backend for retinal fundus or OCT images (current scope: anterior segment / external eye)
- HIPAA / GDPR compliance mechanisms
- Telemedicine integration
- Mobile native app (iOS/Android)
- Multi-language support

---

## 6. User Journeys

### Journey 1 — Full Diagnostic (Primary Flow)

```
1. User opens app → lands on Home page
2. Navigates to "Diagnostic Tool" tab
3. Uploads eye scan → Crop tool opens automatically
4. Adjusts crop → confirms
5. Selects symptom options (pain, vision, itch, etc.)
6. Clicks "Run AI Diagnosis"
7. Views result card: diagnosis, confidence, severity badge
8. Reviews Grad-CAM heatmap (toggle)
9. Browses treatment / doctor's note / symptoms / AI stats tabs
10. Downloads PDF report
11. Asks AI Doctor follow-up question
12. Clicks "Find Nearest Ophthalmologist"
```

### Journey 2 — Education / Research

```
1. User opens "Conditions" page
2. Browses condition cards
3. Clicks a condition → modal with full clinical details
4. Opens "How It Works" page → reads pipeline explanation + training params
```

### Journey 3 — Chat Only

```
1. User opens app (no scan)
2. Clicks floating chat button (bottom-right)
3. Asks a general eye health question
4. Receives structured AI response
5. Clicks a quick-question chip
```

---

## 7. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Inference response time < 10 s on GPU; < 60 s on CPU |
| **Availability** | Target 99.5% uptime for production Docker Compose deploy |
| **Scalability** | Stateless backend allows horizontal scaling behind a load balancer |
| **Accessibility** | WCAG 2.1 AA for all interactive elements; keyboard navigable |
| **Responsiveness** | Mobile-first; works on screens ≥375 px width |
| **Security** | No patient data persisted server-side; CORS restricted in production |
| **Portability** | Runs on Linux/macOS/Windows via Docker |

---

## 8. Constraints

- Models are trained on a specific dataset; performance on out-of-distribution images may be lower
- Grad-CAM is not available for the Adnexal/Eyelid group (single-class pass-through)
- PDF export depends on browser `canvas` API; blocked in some sandboxed environments
- Text-to-speech uses the browser's Web Speech API (not available in all browsers)
- Chat functionality requires an external LLM (Anthropic API or local Ollama) — no fallback

---

## 9. Assumptions

- Users upload clear, well-lit frontal eye photographs
- The application is accessed via a modern browser (Chrome 90+, Firefox 88+, Safari 15+)
- GPU is available for production inference; CPU fallback is acceptable for demos only
- The operator provides either an Anthropic API key or a local Ollama instance

---

## 10. Medical & Ethical Considerations

- The system must always display a medical disclaimer on every page
- Results must never be presented as a clinical diagnosis — language is "AI screening result"
- Emergency conditions (Uveitis, Jaundice) must always trigger visible urgent alerts
- No personally identifiable information (PII) or uploaded images are stored server-side
- The system should encourage — never replace — consultation with a qualified ophthalmologist
