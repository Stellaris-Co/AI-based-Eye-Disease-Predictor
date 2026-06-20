# Application Flow
## OphthalmoAI

---

## 1. Navigation Structure

OphthalmoAI is a single-page application with five top-level views controlled by `activeTab`. There is no URL routing; navigation stays in memory.

```
App (root)
├── Home              ← Default landing page
├── Diagnostic Tool   ← Core screening feature
├── How It Works      ← Pipeline explainer
├── Conditions        ← 7 condition cards + modal detail
└── Medical News      ← Research article feed
```

Navigation:
- **Desktop:** Horizontal pill buttons in the top nav bar
- **Mobile:** Icon + label tabs pinned below the nav bar

A floating chat button is available on the Diagnostic page.

---

## 2. Page-Level Flow

### 2.1 Home Page

```
[Home Page]
├── Hero section
│   ├── "Start Screening" button  → navigates to Diagnostic
│   └── "How it works" button    → navigates to How It Works
│
├── Quick-access grid (4 cards)
│   ├── Diagnostic Tool card     → Diagnostic
│   ├── How It Works card        → How It Works
│   ├── Conditions card          → Conditions
│   └── Medical News card        → News
│
└── Features strip (static — no navigation)
```

### 2.2 Diagnostic Tool — Full Flow

```
[Diagnostic Page]
│
├── STATE: No file uploaded
│   ├── Upload panel with drag/drop label
│   ├── Symptom selectors HIDDEN
│   └── "Run AI Diagnosis" button DISABLED
│
├── EVENT: User clicks upload / drops file
│   ├── File read → object URL created
│   ├── CROP MODAL opens (full-screen overlay)
│   │   ├── User adjusts crop area (pinch/drag)
│   │   ├── "Cancel" → file cleared, back to empty state
│   │   └── "Confirm & Continue" → getCroppedImg() → Blob
│   └── STATE: File set, preview shown
│
├── STATE: File ready, symptom form visible
│   ├── 8 SymptomSelect dropdowns (pain, vision, itch, halos,
│   │   discharge, light sensitivity, floaters, duration)
│   └── "Run AI Diagnosis" button ENABLED
│
├── EVENT: User clicks "Run AI Diagnosis"
│   ├── loading = true, button shows spinner
│   ├── FormData built with: file, pain, vision, itch
│   │   NOTE: halos/discharge/lightSens/spots/duration are
│   │   captured for PDF only — not sent to /predict API
│   ├── POST /predict
│   │   ├── SUCCESS → result state set
│   │   └── ERROR → alert(error message)
│   └── loading = false
│
├── STATE: Result available
│   ├── Result card shown (diagnosis, confidence, severity badge)
│   ├── Clinical alerts strip (if hybrid_warnings present)
│   ├── Heatmap toggle (if heatmap returned)
│   │
│   ├── Tabbed detail panel:
│   │   ├── Treatment tab  (default) — treatment protocol items
│   │   ├── Doctor's Note  — advice, description, visual analysis
│   │   │   └── "Find Nearest Ophthalmologist" → opens Google Maps
│   │   ├── Symptoms tab   — condition symptoms + precautions
│   │   └── AI Stats tab   — probability bar chart per class
│   │
│   ├── Actions:
│   │   ├── TTS button   → speaks diagnosis + advice aloud
│   │   ├── PDF button   → generates 4-page PDF (client-side)
│   │   └── "New Scan"   → resets all state
│   │
│   └── ChatBot (floating)
│       ├── Initialised with diagnosis context
│       └── See Section 2.5
│
└── STATE: New Scan clicked → all state reset to initial
```

### 2.3 How It Works

```
[How It Works Page]
├── 6 pipeline step cards (Upload → Router → Specialist →
│   Symptom Check → Grad-CAM → Report)
├── ASCII model hierarchy diagram
└── Training hyperparameters table
    (all static — no interactions)
```

### 2.4 Conditions Page

```
[Conditions Page]
│
├── 7 condition cards displayed in responsive grid
│
└── EVENT: User clicks a card
    ├── selected = condition object
    └── MODAL opens (fixed overlay with backdrop blur)
        ├── Condition name, group, severity badge
        ├── Description
        ├── Symptoms list
        ├── Treatment list
        ├── Precautions list
        ├── Clinical Note box
        └── "×" button or backdrop click → selected = null → modal closes
```

### 2.5 AI Doctor Chat (ChatBot)

```
[ChatBot — Floating Widget]
│
├── FAB button (bottom-right)
│   ├── Click → isOpen = true, isMinimized = false
│   └── If open: click → isOpen = false
│
├── STATE: isOpen = true
│   ├── Header: title, status dot, context pill, minimize button
│   ├── Disclaimer banner
│   ├── Message thread (scrollable)
│   │   ├── Initial assistant message (changes if diagnosisContext set)
│   │   └── Subsequent messages rendered with role-based styling
│   │
│   ├── Quick Questions (shown only when ≤2 messages)
│   │   └── Click chip → sendMessage(chip text)
│   │
│   ├── Input area
│   │   ├── Textarea (Enter to send, Shift+Enter for newline)
│   │   └── Send button (disabled if empty or loading)
│   │
│   └── EVENT: Message sent
│       ├── User message appended immediately
│       ├── Typing dots shown
│       ├── POST /chat with { message, history, diagnosis_context }
│       ├── SUCCESS → assistant message appended
│       └── ERROR → error message appended as assistant response
│
└── STATE: isMinimized = true
    └── Only header shown; input and messages hidden
```

### 2.6 Medical News

```
[Medical News Page]
├── Category filter pills (All, Research, Technology, Prevention,
│   Treatment, Pediatric)
│
├── EVENT: Click category pill
│   └── activeCategory = category → list filtered client-side
│
├── Article cards (filtered)
│   ├── Category badge, date, read time, source
│   ├── Title and summary
│   ├── Tags
│   └── Featured articles have a star banner
│
└── Disclaimer note at bottom (static)
```

---

## 3. State Management

All state is managed via React `useState` hooks — no external state management library.

### DiagnosticPage state

| Variable | Type | Purpose |
|----------|------|---------|
| `file` | `Blob \| null` | The cropped image file to upload |
| `preview` | `string \| null` | Object URL for the preview `<img>` |
| `heatmap` | `string \| null` | Base64 data URL of the Grad-CAM image |
| `loading` | `boolean` | Controls button state during API call |
| `result` | `object \| null` | Full `/predict` API response |
| `activeTab` | `string` | Active detail tab (treatment/doctor/symptoms/stats) |
| `showHeatmap` | `boolean` | Toggle between original and heatmap image |
| `isSpeaking` | `boolean` | TTS active state |
| `pain/vision/itch/...` | `string` | Symptom form values |
| `crop/zoom/croppedAreaPixels` | various | Cropper state |
| `isCropping` | `boolean` | Show/hide full-screen crop modal |

### ChatBot state

| Variable | Type | Purpose |
|----------|------|---------|
| `isOpen` | `boolean` | Chat panel visibility |
| `isMinimized` | `boolean` | Collapsed header-only view |
| `messages` | `array` | Full conversation history |
| `input` | `string` | Current textarea value |
| `loading` | `boolean` | Awaiting API response |

---

## 4. API Interaction Points

| User Action | API Call | Method |
|------------|----------|--------|
| Click "Run AI Diagnosis" | `/predict` | POST multipart/form-data |
| Send chat message | `/chat` | POST application/json |
| Page load | (none — no API call on load) | — |
| PDF download | (client-side only — no API) | — |
| TTS | (browser Web Speech API — no API) | — |
| "Find Ophthalmologist" | Opens Google Maps URL in new tab | — |

---

## 5. Lifecycle Events

### App startup (frontend)
- Vite dev: hot module reloading active
- Production: static files served by Nginx
- No API calls on page load — system status only checked if user accesses the root `/`

### Backend startup
- `lifespan` async context manager runs model loading
- Models loaded once at startup into module-level globals `ROUTER_MODEL`, `SPECIALIST_MODELS`
- GPU cache cleared on shutdown

### Component cleanup
- `useEffect` cleanup in `DiagnosticPage`: `window.speechSynthesis.cancel()` on unmount
- No WebSockets or polling — all interactions are request/response

---

## 6. Error States

| Condition | User-Facing Behaviour |
|-----------|----------------------|
| Backend offline | `alert()` with "Analysis Error" + error message |
| Model not loaded | `alert()` with "AI diagnostic system offline" |
| File read error | `alert()` from Axios error handler |
| Chat network error | Error text shown as assistant message in chat |
| Grad-CAM fails | Heatmap is `null`; result still shown without heatmap toggle |
| TTS not supported | Button present but `window.speechSynthesis.speak` silently fails |
| PDF canvas error | `console.warn` — PDF downloads with missing images |
