# Backend Schema & API Reference
## OphthalmoAI

**Base URL (local dev):** `http://localhost:8000`  
**Base URL (Docker prod):** `http://localhost:8000` (or via Nginx `/api/` proxy)

---

## 1. Overview

The backend is a **FastAPI** app with 5 HTTP endpoints. Models are loaded once at startup into module globals. Image uploads are processed in memory; files are not persisted to disk.

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

---

### `GET /`

System status overview.

**Response 200:**
```json
{
  "status": "OphthalmoAI System Ready",
  "device": "cuda",
  "router_loaded": true,
  "specialists_loaded": 3,
  "chat_backend": "Anthropic Claude"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Fixed string |
| `device` | string | `"cuda"` or `"cpu"` |
| `router_loaded` | boolean | Whether `ROUTER_MODEL` is not None |
| `specialists_loaded` | integer | Count of entries in `SPECIALIST_MODELS` |
| `chat_backend` | string | `"Anthropic Claude"` \| `"Ollama (model)"` \| `"Not Configured"` |

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

### `POST /predict`

Main inference endpoint. Accepts an eye scan and symptom data; returns a full diagnostic result.

**Request:** `multipart/form-data`

| Field | Type | Required | Allowed Values |
|-------|------|----------|----------------|
| `file` | `UploadFile` | ✅ | JPG, PNG, BMP (any PIL-readable format) |
| `pain` | `string` (Form) | ✅ | `"None"` \| `"Mild"` \| `"Severe"` \| `"Not Sure"` |
| `vision` | `string` (Form) | ✅ | `"No"` \| `"Yes"` \| `"Not Sure"` |
| `itch` | `string` (Form) | ✅ | `"No"` \| `"Yes"` \| `"Not Sure"` |

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

**Response 200 (error — model offline):**
```json
{ "error": "AI diagnostic system offline. Train and load models first (see README)." }
```

**Response 200 (error — inference failed):**
```json
{ "error": "Analysis failed: <exception message>" }
```

> Note: FastAPI returns HTTP 200 even for business-logic errors in this implementation. Check for the `error` key in the response.

#### Inference behaviour by group

| Group | Specialist | Heatmap | Probabilities |
|-------|-----------|---------|---------------|
| Adnexal (group 0) | None (direct) | `null` | `{"Eyelid": 1.0}` |
| Anterior (group 1) | EfficientNet-B4 | base64 JPEG | `{"Cataract": x, "Uveitis": y}` |
| Surface (group 2) | EfficientNet-B4 | base64 JPEG | `{"Conjunctivitis": x, ...}` |

---

### `POST /chat`

AI Doctor chatbot proxy. Routes to Anthropic Claude or Ollama depending on configuration.

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
  "model_used": "anthropic"
}
```

| Field | Values |
|-------|--------|
| `model_used` | `"anthropic"` \| `"ollama"` \| `"none"` |

---

## 5. Symptom Cross-Check Rules

The `analyze_symptoms()` function implements these rules:

```python
Rules:
1. diagnosis == "Conjunctivitis" AND pain == "Severe"
   → "⚠️ Pain Mismatch: Severe pain is unusual for Pink Eye..."

2. vision == "Yes" AND diagnosis in ["Conjunctivitis", "Eyelid"]
   → "⚠️ Vision Loss Warning: Surface/Eyelid conditions rarely affect vision..."

3. itch == "Yes" AND diagnosis == "Conjunctivitis"
   → "✅ Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."

4. diagnosis == "Jaundice"
   → "🚨 URGENT: Scleral Icterus is a systemic emergency..."

5. diagnosis == "Uveitis" AND pain in ["Mild", "Severe"]
   → "🚨 URGENT: Uveitis with pain is sight-threatening..."
```

---

## 6. Medical Data Schema

The `MEDICAL_INFO` dictionary in `backend/medical_data.py` stores clinical information for all 7 conditions.

### Schema per condition

```python
{
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

**Anthropic API parameters:**
```python
model="claude-sonnet-4-20250514"
max_tokens=1024
```

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
| `ANTHROPIC_API_KEY` | string | `""` | Anthropic API key; takes priority over Ollama |
| `OLLAMA_URL` | string | `""` | Ollama base URL, e.g. `http://localhost:11434` |
| `OLLAMA_MODEL` | string | `"llama3.2:3b"` | Ollama model name |
| `FORCE_CPU` | string | `"false"` | Set `"true"` to disable CUDA even if available |
| `MODELS_DIR` | string | `<project_root>/models` | Absolute path to `.pth` files |
| `CORS_ORIGINS` | string | `"*"` | Comma-separated allowed origins |
| `PORT` | integer | `8000` | Uvicorn listen port |
| `HOST` | string | `"0.0.0.0"` | Uvicorn listen host |

---

## 10. CORS Configuration

The backend uses FastAPI's `CORSMiddleware`:

```python
allow_origins=cors_origins,   # parsed from CORS_ORIGINS env var
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"]
```

In development, `CORS_ORIGINS=*` permits all origins. In production, restrict to your frontend domain.
