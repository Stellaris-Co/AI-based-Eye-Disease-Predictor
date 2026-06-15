# OphthalmoAI — Issues & Technical Debt Tracker

> A consolidated list of bugs, inconsistencies, security gaps, and technical debt found across
> the codebase, intended to be triaged into individual GitHub issues. Each entry is written to
> be copy-pasteable as an issue body. Severity legend: 🔴 Critical · 🟠 High · 🟡 Medium ·
> 🟢 Low.
>
> See [`ROADMAP.md`](ROADMAP.md) for how these map onto release milestones, and
> [`docs/ROADMAP.md`](docs/ROADMAP.md) for deeper technical specs referenced from several
> entries below.

## Summary

| Severity | Count | Section |
|---|---|---|
| 🔴 Critical | 5 | [Security & Correctness](#-critical--security--correctness) |
| 🟠 High | 5 | [Functional Bugs & Reliability](#-high--functional-bugs--reliability) |
| 🟡 Medium | 9 | [Code Quality & Consistency](#-medium--code-quality--consistency) |
| 🟢 Low | 5 | [Polish & Nice-to-haves](#-low--polish--nice-to-haves) |
| 🧪 | 3 | [Testing & CI Gaps](#-testing--ci-gaps) |
| 🏗 | 4 | [Infrastructure & Production Gaps](#-infrastructure--production-gaps) |

---

## 🔴 Critical — Security & Correctness

### C1. CORS wildcard combined with `allow_credentials=True`
- **Where:** `backend/main.py`, `CORSMiddleware` setup.
- **Issue:** with the default `CORS_ORIGINS=*`, the middleware is configured with
  `allow_origins=["*"]` **and** `allow_credentials=True`. Per the CORS spec, browsers reject
  credentialed requests against a wildcard origin, so this combination doesn't behave as either
  setting alone would suggest. The app doesn't use cookies today, but this is a latent foot-gun
  for v2.0's session-based auth.
- **Fix:** require an explicit origin list in production (already recommended in
  `PRODUCTION.md`), and either drop `allow_credentials=True` while `CORS_ORIGINS=*`, or fail
  startup with a loud warning when both are set simultaneously.

### C2. No request validation on `/predict`
- **Where:** `backend/main.py`, `POST /predict`.
- **Issue:** there is no file-size limit, MIME-type allow-list, or dimension check before
  `Image.open(io.BytesIO(contents))`. A large or malformed upload consumes memory/CPU before
  any error handling triggers — a trivial DoS vector on an unauthenticated endpoint.
- **Fix:** as drafted in `docs/IMPLEMENTATION_PLAN.md` Issue 4 / `docs/ROADMAP.md` §0.3 —
  enforce `MAX_FILE_SIZE` (e.g. 20 MB), an `ALLOWED_TYPES` allow-list, and a PIL
  `verify()`/`convert("RGB")` check, returning 413/415/422 as appropriate.

### C3. No rate limiting on `/predict` or `/chat`
- **Where:** `backend/main.py`.
- **Issue:** both endpoints are unauthenticated with no per-IP limits. `/predict` is a
  resource-exhaustion vector (CPU/GPU inference); `/chat` is a billing-exhaustion vector since
  it proxies to the Anthropic API using the operator's API key.
- **Fix:** add `slowapi` per the sketch in `docs/ROADMAP.md` §3.4 — a sensible starting point
  is 10/min on `/predict` and 30/min on `/chat`.

### C4. No authentication on inference endpoints
- **Where:** all routes in `backend/main.py`.
- **Issue:** anyone with network access to the backend can run inference or use the AI Doctor
  chat. This is acceptable for a demo, but neither the README nor `PRODUCTION.md` flags it as a
  gap that must be closed before any real deployment.
- **Fix:** JWT + role-based access control as planned in `docs/ROADMAP.md` §3.2 (v2.0). Until
  then, document clearly that the Docker/K8s deployments described in `PRODUCTION.md` should
  sit behind an authenticating reverse proxy if exposed beyond a trusted network.

### C5. LICENSE file contradicts the stated license elsewhere
- **Where:** `LICENSE`, `README.md` ("## License"), `frontend/src/App.jsx` (`Footer`).
- **Issue:**
  - `LICENSE` contains the full **Apache License 2.0** text, "Copyright 2026 Akash Kundu".
  - `README.md` says: *"MIT License — see [LICENSE](LICENSE) for details."*
  - The app's footer renders: *"© 2025 · MIT License"*.
  - This is a real legal inconsistency for anyone trying to determine the project's actual
    license.
- **Fix:** pick one license and make all three consistent — either update `README.md` and the
  footer to say "Apache License 2.0" (matching the existing `LICENSE` file), or replace
  `LICENSE` with the MIT text if that was the intended license.

---

## 🟠 High — Functional Bugs & Reliability

### H1. Only 3 of 8 collected symptoms reach `/predict`
- **Where:** `frontend/src/App.jsx` (`handleAnalyze`), `backend/main.py` (`/predict`,
  `analyze_symptoms`).
- **Issue:** `DiagnosticPage` collects `pain`, `vision`, `itch`, `halos`, `discharge`,
  `lightSens`, `spots`, and `duration`, but `handleAnalyze()` only appends `pain`, `vision`,
  and `itch` to the `FormData`. The other five are used solely for the PDF report and never
  influence the AI's symptom cross-check. Already tracked in `docs/TRD.md` §9 and
  `docs/ROADMAP.md` §0.1.
- **Fix:** expand the `/predict` signature and `analyze_symptoms()` per the code already
  drafted in `docs/ROADMAP.md` §0.1, and add the four missing `formData.append(...)` calls in
  `handleAnalyze()`.

### H2. Hardcoded, dated Anthropic model snapshot
- **Where:** `backend/main.py`, `chat_endpoint` → `model="claude-sonnet-4-20250514"`.
- **Issue:** pinned model snapshots are eventually retired. If/when that happens, `/chat`
  breaks with no code change on this side, and the failure mode is an opaque exception caught
  by the broad `except Exception` block, surfaced to the user as a generic connection error.
- **Fix:** read the model name from an `ANTHROPIC_MODEL` env var (defaulting to a current,
  supported model), and document it in `README.md` / `.env.example` so operators can upgrade
  without a code change.

### H3. Single synchronous Uvicorn worker
- **Where:** `backend/Dockerfile` (`CMD ["python", "-m", "uvicorn", ...]`, no `--workers`),
  `backend/main.py` (module-level model globals).
- **Issue:** documented in `docs/TRD.md` §9. CPU inference can take up to ~10s; concurrent
  requests serialize behind each other and can exceed the 180s Nginx proxy timeout under load.
- **Fix:** medium-term, the Celery/Redis queue in `docs/ROADMAP.md` §3.1 (v3.1). Short-term,
  consider multiple Uvicorn workers with per-worker model copies for CPU deployments (GPU
  deployments still need single-writer access to avoid VRAM contention).

### H4. Backend dependencies are unpinned
- **Where:** `backend/requirements.txt`.
- **Issue:** every dependency uses `>=` with no upper bound, and there's no lock file (unlike
  `frontend/package-lock.json`, which pins exact versions). A fresh `pip install` could pull a
  breaking major version of FastAPI, Pydantic, torchvision, or `grad-cam`, especially risky
  given how tightly `backend/main.py` couples to torchvision's model APIs.
- **Fix:** generate a `requirements.lock` from a known-good build (e.g. via `pip-tools` or
  `pip freeze`), have `backend/Dockerfile` install from the lock file, and keep
  `requirements.txt` as the human-edited "intent" file that the lock is regenerated from.

### H5. Broken `<meta description>` tag
- **Where:** `frontend/index.html`.
- **Issue:** `<meta description="OphthalmoAI - AI-Powered Eye Disease Detection" />` is invalid
  HTML — `<meta>` tags require `name` and `content` attributes. As written, this tag has no
  effect on SEO or link-preview cards.
- **Fix:** `<meta name="description" content="OphthalmoAI - AI-Powered Eye Disease Detection" />`,
  and consider adding `og:title` / `og:description` / `og:image` for richer link previews.

---

## 🟡 Medium — Code Quality & Consistency

### M1. Dead file `frontend/src/App.css`
- **Where:** `frontend/src/App.css`.
- **Issue:** a Vite template leftover that is never imported anywhere. Already noted in
  `docs/TRD.md` §9 / `docs/IMPLEMENTATION_PLAN.md` Issue 2.
- **Fix:** delete the file.

### M2. No Vite dev proxy for `/api`
- **Where:** `frontend/vite.config.js`.
- **Issue:** noted in `docs/TRD.md` §9 / `docs/IMPLEMENTATION_PLAN.md` Issue 3. Without a
  proxy, every developer must set `VITE_API_URL` manually or hit CORS issues against the
  backend's default `CORS_ORIGINS=*` (which, combined with C1, is itself worth fixing).
- **Fix:** add the proxy block from `docs/ROADMAP.md` §0.2. Decide on one convention end-to-end
  — either dev also targets `/api` (stripped by the proxy, mirroring `frontend/nginx.conf`), or
  document why dev and prod intentionally differ.

### M3. Clinical condition data duplicated between backend and frontend
- **Where:** `backend/medical_data.py` (`MEDICAL_INFO`) and `frontend/src/App.jsx`
  (`ConditionsPage` → local `conditions` array).
- **Issue:** both files hardcode descriptions, symptoms, treatments, precautions, and severity
  strings for the same 7 conditions, and they have already drifted. Examples:
  - Cataract severity: backend `"Moderate to Severe (depending on opacity density)"` vs.
    frontend `"Moderate–Severe"`.
  - Jaundice severity: backend `"High (Systemic Medical Emergency)"` vs. frontend
    `"High — Systemic Emergency"`.
  - Uveitis severity: backend `"High (Sight-Threatening Emergency)"` vs. frontend
    `"High — Sight-Threatening"`.
  - Conjunctivitis severity: backend `"Low (usually self-limiting, but contagious)"` vs.
    frontend `"Low (Contagious)"`.
- **Fix:** expose a `GET /conditions` endpoint backed by `MEDICAL_INFO` (plus any
  frontend-only fields like card `color`), and have `ConditionsPage` fetch from it instead of
  maintaining a parallel array. Tracked for v2.1 in `ROADMAP.md`.

### M4. Personal dev-tunnel hostname committed to `vite.config.js`
- **Where:** `frontend/vite.config.js` → `server.allowedHosts: ['opthalmoai.loca.lt']`.
- **Issue:** a specific (and misspelled — "opthalmoai" vs. "ophthalmoai") LocalTunnel hostname
  from the original developer's machine is committed to shared config.
- **Fix:** remove it, or make it configurable via an env var (e.g. `VITE_ALLOWED_HOSTS`,
  comma-separated) read in `vite.config.js`, defaulting to none.

### M5. Unused Inter font loaded in `index.html`
- **Where:** `frontend/index.html`, `frontend/tailwind.config.js`, `frontend/src/index.css`.
- **Issue:** `index.html` preconnects to Google Fonts and loads "Inter", and
  `tailwind.config.js` sets `fontFamily.sans = ['Inter', 'sans-serif']`. The actual design
  system (`docs/UI_UX_BRIEF.md` §3, `frontend/src/index.css`) uses **Sora** (display) and
  **DM Sans** (body), loaded via a separate `@import` in `index.css`. Inter appears to be dead
  weight — an extra font request with no visible effect.
- **Fix:** remove the Inter `<link>` tags from `index.html`. If Tailwind's `font-sans` utility
  is ever used, update `tailwind.config.js` to reference Sora/DM Sans instead.

### M6. `/predict` and `/chat` return HTTP 200 even on errors
- **Where:** `backend/main.py`, both endpoints; documented behaviour in
  `docs/BACKEND_SCHEMA.md` §4.
- **Issue:** business-logic errors (model not loaded, invalid image, inference exception) are
  returned as `{"error": "..."}` with HTTP 200. This requires every client to inspect the
  response body, and makes a "200 with an error body" look healthy to generic uptime/APM
  tooling.
- **Fix:** when convenient (ideally alongside the v1.2 API-versioning work), raise
  `HTTPException` with appropriate status codes — 503 for "model not loaded", 422 for "invalid
  image", 500 for unexpected inference failures — while keeping a v1-compatible response shape
  if needed for the current frontend.

### M7. `specialist_eyelid.pth` / `train_eyelid.py` are trained but unused
- **Where:** `scripts/train_eyelid.py`, `backend/main.py` (`SPECIALIST_MODELS[0]` is
  `type: "direct"`).
- **Issue:** `docs/TRD.md` §5.3 confirms the Adnexal/Eyelid specialist is trained with MSE loss
  but never loaded at inference — the router's classification is returned directly as
  "Eyelid". This is harmless but confusing for new contributors who find a training script
  whose output is never consumed.
- **Fix:** either (a) remove the script and stop documenting it as part of the training
  pipeline, or (b) actually wire it in as a confidence-refinement/second-opinion step for
  Adnexal cases and document the rationale either way.

### M8. `ChatBox` only renders `**bold**` Markdown
- **Where:** `frontend/src/ChatBox.jsx`, `formatMessage()`.
- **Issue:** `formatMessage` only splits on `**`. `OPHTHALMOLOGY_SYSTEM_PROMPT` in
  `backend/main.py` explicitly instructs the model to "use bullet points where helpful", so
  responses containing `- item` or `1. item` lines render as literal dashes/numbers rather
  than formatted lists.
- **Fix:** either extend `formatMessage` to handle line-based lists, or swap in a small, safe
  Markdown renderer (e.g. `react-markdown` with a restrictive, no-raw-HTML configuration).

### M9. `frontend/package.json` version stuck at `0.0.0`
- **Where:** `frontend/package.json`.
- **Issue:** still the Vite scaffold default, while the backend declares
  `FastAPI(..., version="2.0.0")`. Minor, but worth tracking frontend releases meaningfully.
- **Fix:** bump alongside backend versioning, or adopt a shared version source (e.g. a root
  `VERSION` file referenced by both).

---

## 🟢 Low — Polish & Nice-to-haves

### L1. Favicon is still the default Vite logo
- **Where:** `frontend/index.html` (`<link rel="icon" ... href="/vite.svg" />`),
  `frontend/public/vite.svg`.
- **Issue:** the browser tab shows the stock Vite icon instead of OphthalmoAI branding (the
  `Eye` icon used throughout the app).
- **Fix:** generate a favicon from the `Eye` mark (cyan `#0891B2` on transparent/navy) and
  replace `vite.svg`.

### L2. No `.env.example` in the repo
- **Where:** repo root.
- **Issue:** `.gitignore` and `.dockerignore` both special-case `.env.example`/`.env.sample` as
  *not* ignored, but no such file is present. New contributors must reconstruct the `.env`
  shape from `README.md` prose.
- **Fix:** add `.env.example` mirroring the README's "Configuration (.env)" section, with
  placeholder values and inline comments for each variable.

### L3. Hardcoded copyright year in the footer
- **Where:** `frontend/src/App.jsx`, `Footer` → `<span>© 2025 · MIT License</span>`.
- **Issue:** will silently go stale every year, and is also part of the license inconsistency
  in C5.
- **Fix:** `© {new Date().getFullYear()} · <license>`.

### L4. Emoji-prefixed clinical alert strings
- **Where:** `backend/main.py` (`analyze_symptoms`), `backend/medical_data.py`.
- **Issue:** alert text returned by the API embeds emoji (⚠️ 🚨 ✅) directly in the message
  string. Fine for the current single-language web UI, but couples presentation to data and
  complicates future i18n or non-visual clients (SMS, FHIR export, screen readers).
- **Fix:** separate a `severity`/`type` field (`info` | `warning` | `urgent`) from the
  human-readable message text; let each client choose its own iconography.

### L5. Modal focus trap not implemented
- **Where:** `frontend/src/App.jsx` — `ConditionsPage` modal, `DiagnosticPage` crop modal.
- **Issue:** acknowledged in `docs/UI_UX_BRIEF.md` §9 — keyboard `Tab` can escape the overlay
  to elements behind it.
- **Fix:** add a focus-trap (custom hook or a small library) for both modals as part of the
  accessibility pass.

---

## 🧪 Testing & CI Gaps

### T1. No automated tests
- **Where:** `backend/`, `frontend/`.
- **Issue:** neither side has test files, despite `docs/ROADMAP.md` §7.2 describing a target
  `tests/` layout.
- **Fix:** start with the highest-value cases — `analyze_symptoms()`'s rule table, `/predict`
  against a mocked router/specialist returning fixed logits, `/health` and `/ready` under
  various load states, and React Testing Library smoke tests for `DiagnosticPage` and
  `ChatBox`.

### T2. No CI pipeline
- **Where:** repo root (no `.github/workflows/`).
- **Issue:** `docs/ROADMAP.md` §7.1 includes a ready-to-adapt GitHub Actions workflow covering
  backend tests, frontend lint/build, dependency audits, and Docker builds — none of it is
  wired up.
- **Fix:** add `.github/workflows/main.yml` based on that draft once T1 lands.

### T3. Lint not enforced anywhere
- **Where:** `frontend/eslint.config.js`.
- **Issue:** `npm run lint` works locally, but nothing runs it automatically (no pre-commit
  hook, no CI).
- **Fix:** fold into the CI pipeline from T2; optionally add a pre-commit hook for fast local
  feedback.

---

## 🏗 Infrastructure & Production Gaps

### I1. GPU instructions don't match the GPU-less backend image
- **Where:** `PRODUCTION.md` ("GPU Node Scheduling" section), `backend/Dockerfile`.
- **Issue:** `PRODUCTION.md` tells operators to add `nvidia.com/gpu: 1` resource limits and
  remove `FORCE_CPU: "true"` to enable GPU inference — but `backend/Dockerfile` **always**
  installs the CPU-only PyTorch wheel
  (`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`). With that
  image, `torch.cuda.is_available()` is `False` regardless of the node's GPU, so the documented
  GPU setup has no effect.
- **Fix:** add a `backend/Dockerfile.gpu` (CUDA-enabled base image + `cu124` torch wheel) and
  reference it explicitly from the GPU section of `PRODUCTION.md`, or clearly state that the
  shipped image is CPU-only and GPU support requires a custom build.

### I2. No TLS configuration in the example Ingress
- **Where:** `k8s/ingress.yaml`.
- **Issue:** the Ingress defines a plain-HTTP rule for `ophthalmoai.local` with no `tls:`
  section or cert-manager annotations, even though `PRODUCTION.md` and `docs/ROADMAP.md` §6.3
  both assume HTTPS termination at the edge.
- **Fix:** add a commented-out `tls:` block and a cert-manager annotation example so production
  users have a documented starting point.

### I3. No monitoring stack wired up
- **Where:** repo root / `docker-compose.yml`.
- **Issue:** `docs/ROADMAP.md` §5 specifies Prometheus, Grafana, Loki, and Sentry, but no
  `/metrics` endpoint or `docker-compose.monitoring.yml` exists yet.
- **Fix:** lower priority until the v1.2 observability work (structured logging, `/metrics`)
  lands; then add the compose file from `docs/ROADMAP.md` §5.4.

### I4. In-memory-only image handling needs a deliberate decision before "scan history" ships
- **Where:** `backend/main.py` (`/predict` reads `UploadFile` into memory, never persists).
- **Issue:** this is currently a *feature* — no PHI is stored server-side, matching
  `docs/PRD.md` §10's privacy requirements. However, the v2.0 "scan history" milestone
  (`docs/ROADMAP.md` §8.1) implies persisting images, which is a significant privacy/security
  posture change that needs explicit design (encryption at rest, retention policy, consent),
  not an incidental side effect of adding a database table.
- **Fix:** when v2.0 planning starts, treat image storage as its own design doc using
  `docs/ROADMAP.md` §6.2 (S3 + KMS) as the baseline, with retention and consent explicitly
  specified.

---

## Cross-references

- [`docs/TRD.md`](docs/TRD.md) §9 — "Known Limitations & Technical Debt"
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) §3 — "Known Issues & Recommended
  Fixes"
- [`docs/ROADMAP.md`](docs/ROADMAP.md) §0 — "Fix Known Issues First (Zero-Effort Wins)"
- [`ROADMAP.md`](ROADMAP.md) — how these issues map onto release milestones
