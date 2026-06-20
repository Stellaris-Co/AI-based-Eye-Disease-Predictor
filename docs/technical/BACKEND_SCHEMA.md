# Backend Schema & API Reference
## OphthalmoAI

**Base URL (local dev):** `http://localhost:8000`  
**Base URL (Docker prod):** `http://localhost:8000` (or via Nginx `/api/` proxy)

---

## 1. Overview

The backend is a **FastAPI** app with 6 HTTP endpoints. Models are loaded once at startup into module globals. Image uploads are processed in memory; files are not persisted to disk. `/predict` and `/chat` are rate-limited via `slowapi`.

---

## 2. Startup & Model Loading

Models are loaded via FastAPI's `lifespan` async context manager on application startup.

### Loading sequence

```
1. Build router architecture (MobileNetV3-Large, 3 output classes)
2. Load router.pth → router.to(device).eval()
3. For each group in HIERARCHY:
   a. If single class (Adnexal/Eyelid): register as "direct" pass-through
   b. Otherwise: build EfficientNet-B4 with N output classes
      → load specialist_*.pth → model.to(device).eval()
4. Yield (app is now ready to serve requests)
5. On shutdown: gc.collect() + torch.cuda.empty_cache()
```

### HIERARCHY constant

```python
HIERARCHY = {
    0: {
        'name': 'Adnexal Oculoplastic',
        'model_file': 'specialist_eyelid.pth',
        'classes': ['Eyelid']          # Single class → direct pass-through
    },
    1: {
        'name': 'Anterior Segment Pathology',
        'model_file': 'specialist_anterior.pth',
        'classes': ['Cataract', 'Uveitis']
    },
    2: {
        'name': 'Ocular Surface Disorders',
        'model_file': 'specialist_surface.pth',
        'classes': ['Conjunctivitis', 'Jaundice', 'Normal', 'Pterygium']
    }
}
```

---

## 3. Image Pre-processing

Applied identically to all inference inputs:

```python
transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
```

Output tensor shape: `[1, 3, 380, 380]` (batch of 1).

---

## 4. Endpoints

### `GET /`

System status overview.

**Response 200:**
```json
{
  "status": "OphthalmoAI System Ready",
  "device": "cuda",
  "router_loaded": true,
  "specialists_loaded": 3,
  "chat_backend": "Google Gemini (gemini-2.0-flash)"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Fixed string |
| `device` | string | `"cuda"` or `"cpu"` |
| `router_loaded` | boolean | Whether `ROUTER_MODEL` is not None |
| `specialists_loaded` | integer | Count of entries in `SPECIALIST_MODELS` |
| `chat_backend` | string | `"Google Gemini (model)"` \| `"Ollama (model)"` \| `"Not Configured"` |

---

### `GET /health`

Simple liveness probe. Always returns 200 if the process is running.

**Response 200:**
```json
{ "ok": true, "device": "cuda" }
```

---

### `GET /ready`

Readiness probe. Returns 503 if the router model is not loaded.

**Response 200 (ready):**
```json
{ "ok": true, "router_loaded": true, "specialists_loaded": 3 }
```

**Response 503 (not ready):**
```json
{ "ok": false, "router_loaded": false, "specialists_loaded": 0 }
```

---

### `GET /conditions`

Returns clinical metadata for all 7 detectable conditions, sourced directly from `backend/medical_data.py` (`MEDICAL_INFO`). This is the single source of truth used by both the AI's clinical reference lookups and the frontend's Conditions page — the frontend no longer maintains a separate hardcoded copy of this data.

**Response 200:**
```json
{
  "conditions": [
    {
      "key": "Conjunctivitis",
      "name": "Conjunctivitis",
      "group": "Ocular Surface",
      "color": "#10B981",
      "description": "Conjunctivitis, commonly known as 'Pink Eye'...",
      "symptoms": ["..."],
      "treatment": ["..."],
      "precautions": ["..."],
      "severity": "Low (usually self-limiting, but contagious)",
      "advice": "..."
    }
  ]
}
```

---

### `POST /predict`

Main inference endpoint. Accepts an eye scan and symptom data; returns a full diagnostic result. Rate limited (default `10/minute` per IP, configurable via `PREDICT_RATE_LIMIT`).

**Request:** `multipart/form-data`

| Field | Type | Required | Allowed Values |
|-------|------|----------|----------------|
| `file` | `UploadFile` | ✅ | JPG, PNG, BMP, WEBP — max `MAX_FILE_SIZE_BYTES` (default 20 MB) |
| `pain` | `string` (Form) | ✅ | `"None"` \| `"Mild"` \| `"Severe"` \| `"Not Sure"` |
| `vision` | `string` (Form) | ✅ | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `itch` | `string` (Form) | ✅ | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `halos` | `string` (Form) | ❌ (default `"No"`) | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `discharge` | `string` (Form) | ❌ (default `"None"`) | `"None"` \| `"Watery"` \| `"Thick/Yellow"` \| `"Not Sure"` |
| `light_sens` | `string` (Form) | ❌ (default `"No"`) | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `floaters` | `string` (Form) | ❌ (default `"No"`) | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `duration` | `string` (Form) | ❌ (default `"Not Sure"`) | `"<1 day"` ... `">1 month"` \| `"Not Sure"` |

**Response 200 (success):**
```json
{
  "group_name": "Ocular Surface Disorders",
  "diagnosis": "Conjunctivitis",
  "confidence": 94.72,
  "heatmap": "data:image/jpeg;base64,/9j/4AAQ...",
  "probabilities": {
    "Conjunctivitis": 0.9472,
    "Jaundice": 0.0213,
    "Normal": 0.0182,
    "Pterygium": 0.0133
  },
  "hybrid_warnings": [
    "✅ Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."
  ],
  "hybrid_warnings_structured": [
    { "severity": "info", "message": "Symptom Match: Itchiness strongly supports Allergic Conjunctivitis." }
  ],
  "details": {
    "description": "Conjunctivitis, commonly known as 'Pink Eye'...",
    "analysis": "The bulbar conjunctiva exhibits significant hyperemia...",
    "symptoms": ["Pink or red in white of eye", "..."],
    "treatment": ["Artificial tears...", "..."],
    "precautions": ["Do not touch or rub your eyes", "..."],
    "severity": "Low (usually self-limiting, but contagious)",
    "advice": "If discharge is thick/yellow or pain is moderate..."
  }
}
```

`hybrid_warnings` is the legacy emoji-prefixed string list, kept for backward compatibility. `hybrid_warnings_structured` carries the same alerts as `{"severity": "info"|"warning"|"urgent", "message": "..."}` objects, with presentation (icon/emoji) left to the client — useful for i18n, screen readers, or non-visual clients.

**Error responses** are now real HTTP status codes with a `detail` field (previously these were returned as `200 OK` with an `error` key):

| Status | Cause |
|--------|-------|
| `413` | Upload exceeds `MAX_FILE_SIZE_BYTES` |
| `415` | Unsupported `Content-Type` (not in the image MIME allow-list) |
| `422` | File is not a valid/decodable image |
| `503` | Router or specialist model not loaded |
| `429` | Rate limit exceeded |
| `500` | Unexpected inference failure |

```json
{ "detail": "AI diagnostic system offline. Train and load models first (see README)." }
```

#### Inference behaviour by group

| Group | Specialist | Heatmap | Probabilities |
|-------|-----------|---------|---------------|
| Adnexal (group 0) | None (direct) | `null` | `{"Eyelid": 1.0}` |
| Anterior (group 1) | EfficientNet-B4 | base64 JPEG | `{"Cataract": x, "Uveitis": y}` |
| Surface (group 2) | EfficientNet-B4 | base64 JPEG | `{"Conjunctivitis": x, ...}` |

---

### `POST /chat`

AI Doctor chatbot proxy. Routes to Google Gemini or Ollama depending on configuration. Rate limited (default `30/minute` per IP, configurable via `CHAT_RATE_LIMIT`).

**Request:** `application/json`

```json
{
  "message": "string (required)",
  "history": [
    { "role": "user", "content": "string" },
    { "role": "assistant", "content": "string" }
  ],
  "diagnosis_context": {
    "diagnosis": "Conjunctivitis",
    "confidence": 94.72,
    "group_name": "Ocular Surface Disorders",
    "details": { "severity": "Low", "advice": "..." }
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `message` | string | ✅ | Current user message |
| `history` | array | ✅ | Previous turns (can be empty `[]`); `role` must be `"user"` or `"assistant"` |
| `diagnosis_context` | object \| null | ❌ | If provided, appended to the system prompt |

**Response 200:**
```json
{
  "reply": "Conjunctivitis (Pink Eye) is an inflammation of...",
  "model_used": "gemini"
}
```

| Field | Values |
|-------|--------|
| `model_used` | `"gemini"` \| `"ollama"` \| `"none"` |

---

## 5. Symptom Cross-Check Rules

The `analyze_symptoms()` / `analyze_symptoms_structured()` functions implement these rules (all 8 symptom fields are evaluated, not just `pain`/`vision`/`itch`):

```
1. diagnosis == "Conjunctivitis" AND pain == "Severe"
   → warning: "Pain Mismatch: Severe pain is unusual for Pink Eye..."

2. vision == "Yes" AND diagnosis in ["Conjunctivitis", "Eyelid"]
   → warning: "Vision Loss Warning: Surface/Eyelid conditions rarely affect vision..."

3. itch == "Yes" AND diagnosis == "Conjunctivitis"
   → info: "Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."

4. diagnosis == "Jaundice"
   → urgent: "URGENT: Scleral Icterus is a systemic emergency..."

5. diagnosis == "Uveitis" AND pain in ["Mild", "Severe"]
   → urgent: "URGENT: Uveitis with pain is sight-threatening..."

6. halos == "Yes" AND diagnosis == "Cataract"
   → info: "Symptom Match: Halos around lights strongly support a Cataract diagnosis."

7. floaters == "Yes" AND diagnosis not in ["Uveitis", "Normal"]
   → warning: "Floaters Reported: Consider ruling out Vitreous Detachment or Retinal Tear..."

8. light_sensitivity == "Yes" AND diagnosis == "Uveitis"
   → urgent: "URGENT: Light sensitivity with Uveitis is sight-threatening..."

9. discharge == "Thick/Yellow" AND diagnosis == "Conjunctivitis"
   → info: "Symptom Match: Thick/yellow discharge supports Bacterial Conjunctivitis."

10. duration == ">1 month" AND diagnosis in ["Conjunctivitis", "Eyelid"]
    → warning: "Chronic Duration: Symptoms lasting over a month warrant evaluation..."
```

Each rule's severity (`info` | `warning` | `urgent`) maps to the emoji prefix (`✅` | `⚠️` | `🚨`) used in the legacy `hybrid_warnings` string list.

---

## 6. Medical Data Schema

The `MEDICAL_INFO` dictionary in `backend/medical_data.py` stores clinical information for all 7 conditions, and is also exposed via `GET /conditions`.

### Schema per condition

```python
{
    'name':         str,       # Display name (e.g. "Eyelid Conditions" for key "Eyelid")
    'group':        str,       # Friendly anatomical group label for the frontend
    'color':        str,       # Accent hex color for condition cards
    'analysis':     str,       # Visual/clinical analysis from AI perspective
    'description':  str,       # Lay-person description of the condition
    'symptoms':     list[str], # Common presenting symptoms
    'treatment':    list[str], # Treatment options ordered by first-line preference
    'precautions':  list[str], # Self-care and preventive measures
    'severity':     str,       # Human-readable severity string
    'advice':       str,       # Clinical recommendation / call to action
}
```

### Keys present in MEDICAL_INFO

```
'Cataract'
'Conjunctivitis'
'Eyelid'
'Jaundice'
'Uveitis'
'Normal'
'Pterygium'
```

If a diagnosis is returned that has no entry in `MEDICAL_INFO`, the backend returns a default empty structure with `"Please consult an ophthalmologist."` advice.

---

## 7. Pydantic Models

```python
class ChatMessage(BaseModel):
    role: str        # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    diagnosis_context: Optional[Dict[str, Any]] = None
```

---

## 8. LLM System Prompt

The backend uses a fixed `OPHTHALMOLOGY_SYSTEM_PROMPT` string for all chat requests. When `diagnosis_context` is provided, the following is appended:

```
--- CURRENT PATIENT AI SCREENING RESULT ---
Detected Condition: <diagnosis>
AI Confidence: <confidence>%
Anatomical Group: <group_name>
Severity: <severity>
Clinical Advice: <advice>
Note: This is an AI screening result only, not a clinical diagnosis.
```

**Google Gemini parameters:**
```python
model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# system prompt passed as system_instruction at model construction time
genai.GenerativeModel(model_name=model_name, system_instruction=system)
```

Conversation history is translated from the app's `{"role": "user"|"assistant", "content": "..."}` shape into Gemini's expected `{"role": "user"|"model", "parts": ["..."]}` shape (Gemini uses `"model"` rather than `"assistant"` for AI turns).

**Ollama parameters:**
```python
{
  "temperature": 0.7,
  "num_gpu": 0    # CPU only — change if VRAM headroom available
}
```

---

## 9. Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GEMINI_API_KEY` | string | `""` | Google Gemini API key; takes priority over Ollama |
| `GEMINI_MODEL` | string | `"gemini-2.0-flash"` | Gemini model name used by `/chat` |
| `OLLAMA_URL` | string | `""` | Ollama base URL, e.g. `http://localhost:11434` |
| `OLLAMA_MODEL` | string | `"llama3.2:3b"` | Ollama model name |
| `FORCE_CPU` | string | `"false"` | Set `"true"` to disable CUDA even if available |
| `MODELS_DIR` | string | `<project_root>/models` | Absolute path to `.pth` files |
| `MAX_FILE_SIZE_BYTES` | integer | `20971520` (20 MB) | Max accepted upload size for `/predict` |
| `CORS_ORIGINS` | string | `"*"` | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | string | `"false"` | Must stay `"false"` while `CORS_ORIGINS="*"`; the app refuses to start otherwise |
| `PREDICT_RATE_LIMIT` | string | `"10/minute"` | Per-IP rate limit for `/predict` (requires `slowapi`) |
| `CHAT_RATE_LIMIT` | string | `"30/minute"` | Per-IP rate limit for `/chat` (requires `slowapi`) |
| `PORT` | integer | `8000` | Uvicorn listen port |
| `HOST` | string | `"0.0.0.0"` | Uvicorn listen host |

---

## 10. CORS Configuration

The backend uses FastAPI's `CORSMiddleware`:

```python
allow_origins=cors_origins,             # parsed from CORS_ORIGINS env var
allow_credentials=allow_credentials,    # parsed from CORS_ALLOW_CREDENTIALS env var
allow_methods=["*"],
allow_headers=["*"]
```

In development, `CORS_ORIGINS=*` permits all origins. In production, restrict to your frontend domain. The app **refuses to start** if `CORS_ORIGINS=*` is combined with `CORS_ALLOW_CREDENTIALS=true`, since browsers reject credentialed requests against a wildcard origin and the combination is unsafe by spec.
