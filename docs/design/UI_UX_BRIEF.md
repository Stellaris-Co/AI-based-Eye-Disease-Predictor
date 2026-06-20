# UI Notes
## OphthalmoAI

---

## 1. Direction

The UI should feel like a small medical screening tool: clean, direct, and easy to scan. It should avoid looking like a marketing page, especially in the diagnostic flow.

Working notes:
- Keep the result and severity easy to find.
- Critical conditions such as Jaundice and Uveitis need a clear warning state.
- Show confidence, probability bars, and Grad-CAM output where they help explain the result.
- Put longer clinical text in tabs or modals so the main result stays readable.

---

## 2. Colour Palette

### Brand Colours

| Token | Hex | Usage |
|-------|-----|-------|
| `--accent` | `#0891B2` (Cyan 600) | Primary CTA buttons, highlights, links |
| `--accent-hover` | `#0E7490` (Cyan 700) | Button hover state |
| `--accent-bg` | `#F0F9FF` (Cyan 50) | Tinted backgrounds, info panels |
| `--accent-border` | `#BAE6FD` (Cyan 200) | Subtle borders for accented containers |
| `--accent-text` | `#0369A1` (Sky 700) | Text on accent backgrounds |
| `--navy` | `#0F2040` | Page headings, nav brand, dark backgrounds |
| `--navy-mid` | `#1E3A5F` | Hover states for dark backgrounds |

### Semantic / State Colours

| Token | Hex | Usage |
|-------|-----|-------|
| Success | `#10B981` (Emerald 500) | "Normal" diagnosis, healthy indicators |
| Success BG | `#F0FDF4` | Normal result banner |
| Warning | `#F59E0B` (Amber 500) | Clinical alert icons, warning borders |
| Warning BG | `#FFFBEB` | Warning panels, disclaimer banners |
| Warning Text | `#92400E` | Text on warning backgrounds |
| Danger | `#EF4444` (Red 500) | High severity conditions |
| Danger BG | `#FEF2F2` | Critical alert panels |
| Info | `#0891B2` | AI stats, probability bars (dominant) |
| Info Light | `#7DD3FC` | Probability bars (secondary classes) |

### Neutral Palette (Slate scale)

| Use | Token |
|-----|-------|
| Page background | `#F8FAFC` (Slate 50) |
| Card/surface | `#FFFFFF` |
| Raised surface | `#FAFBFC` |
| Border default | `#E2E8F0` (Slate 200) |
| Border subtle | `#F1F5F9` (Slate 100) |
| Text primary | `#0F172A` (Slate 900) |
| Text secondary | `#475569` (Slate 600) |
| Text tertiary | `#94A3B8` (Slate 400) |

---

## 3. Typography

### Font Families

| Role | Family | Weights |
|------|--------|---------|
| Display / Headings | **Sora** | 300, 400, 500, 600, 700 |
| Body / UI | **DM Sans** | 300, 400, 500, 600, 700 (+ italic 400) |
| Code / Monospace | System monospace (`font-mono`) | — |

Both fonts are loaded via Google Fonts with `display=swap`.

### Type Scale

| Element | Size | Weight | Family |
|---------|------|--------|--------|
| `h1` (hero) | `text-4xl` / `text-5xl` | 600 | Sora |
| `h2` (page title) | `text-2xl` | 600 | Sora |
| `h3` (card title) | `text-sm` | 600 | DM Sans |
| Body text | `text-sm` (14 px) | 400 | DM Sans |
| Small / metadata | `text-xs` (12 px) | 400–500 | DM Sans |
| Section label | 11 px, uppercase, 0.1em tracking | 600 | DM Sans |
| Monospace detail | `text-xs font-mono` | 400 | System |

**Letter spacing:**
- Display headings: `-0.025em` to `-0.03em`
- Section labels: `0.1em` (wide)
- Body: default (0)

---

## 4. Spacing & Layout

### Grid

- Max content width: `max-w-6xl` (1152 px)
- Horizontal padding: `px-4 sm:px-6 lg:px-8`
- Responsive diagnostic layout: `lg:grid-cols-12` → upload panel is `lg:col-span-5`, results are `lg:col-span-7`

### Spacing Tokens (Tailwind)

| Use | Value |
|-----|-------|
| Section padding | `py-12` |
| Card padding | `p-5` / `p-6` |
| Inline gap | `gap-2` / `gap-3` |
| Section gap | `space-y-4` / `space-y-5` |

---

## 5. Component Patterns

### 5.1 Cards

All cards follow:
- Background: `#FFFFFF`
- Border: `1px solid #E2E8F0` (Slate 200)
- Border radius: `rounded-xl` (12 px)
- Hover: `hover:border-slate-300 hover:shadow-md transition-all`

**Clickable cards** add `cursor-pointer` and a `<ChevronRight>` icon as a visual affordance.

**Severity cards** use a left-border accent:
```css
border-left: 4px solid <condition-color>;
```

### 5.2 Buttons

**Primary:**
```css
background: #0891B2;
color: white;
padding: 0.625rem 1.125rem;
border-radius: 8px;
font-weight: 600;
font-size: 0.875rem;
```
Hover: `#0E7490`. Disabled: `#94A3B8`, `cursor: not-allowed`.

**Secondary / Ghost:**
```css
background: white;
border: 1px solid #E2E8F0;
color: #475569;
```
Hover: `background: #F8FAFC`, `border-color: #CBD5E1`.

**Icon-only:**
```css
padding: 8px;
border-radius: 8px;
border: 1px solid #E2E8F0;
```

### 5.3 Badges

**Severity Badge (`<SeverityBadge>`):**
- High severity: `bg-red-50 text-red-700`
- Low severity: `bg-emerald-50 text-emerald-700`
- Moderate: `bg-amber-50 text-amber-700`
- Font size: 11 px, weight 500

**Tag / label pills:**
```css
background: #F0F9FF;
color: #7DD3FC;
border: 1px solid #E0F2FE;
font-size: 10px;
padding: 4px 10px;
border-radius: 6px;
```

### 5.4 Form Selects (`<SymptomSelect>`)

```css
background: #FFFFFF;
border: 1px solid #E2E8F0;
border-radius: 8px;
padding: 8px 10px;
font-size: 14px;
appearance: none;  /* custom ChevronDown icon */
```

Focus: `border-color: #0891B2; box-shadow: 0 0 0 2px rgba(8,145,178,0.12)`.

### 5.5 Tabs (`<TabButton>`)

Active state:
```css
color: #0E7490 (cyan-700);
border-bottom: 2px solid #0891B2 (cyan-600);
background: rgba(8,145,178,0.04);
```

Inactive: `color: #64748B`, `border-bottom: 2px solid transparent`.

### 5.6 Modals / Overlays

Backdrop:
```css
background: rgba(15, 32, 64, 0.7);
backdrop-filter: blur(4px);
```

Modal container:
```css
background: white;
border-radius: 16px;
box-shadow: 0 25px 50px rgba(0,0,0,0.2);
max-height: 90vh;
overflow-y: auto;
```

### 5.7 Probability Bar (`<ProbabilityBar>`)

- Track: `height: 6px; background: #F1F5F9; border-radius: 99px`
- Fill: animated (`transition: width 0.75s cubic-bezier(0.16, 1, 0.3, 1)`)
- Dominant class (>55%): `#0891B2`; others: `#7DD3FC`

### 5.8 Crop Modal

- Full-screen fixed overlay with `background: rgba(15,32,64,0.95)`
- White instructional text above cropper
- Confirm / Cancel buttons at bottom (full-width row)
- Pinch-to-zoom and drag reposition instructions shown below

---

## 6. Animation

All transitions use `cubic-bezier(0.16, 1, 0.3, 1)` — a snappy ease-out curve.

| Animation | Keyframes | Usage |
|-----------|-----------|-------|
| `animate-fade-up` | `opacity 0→1, translateY 8px→0` | Page sections, result cards |
| `animate-fade-in` | `opacity 0→1` | Tab content, alerts |
| `animate-scale-in` | Same as fade-up | Secondary cards |
| Stagger | `nth-child` delays 40 ms each | Symptom selects grid |
| Probability bars | `width` transition 750 ms | AI stats tab |
| Bounce dots (typing) | `@keyframes bounce` | Chat loading indicator |

**Duration:** 300–400 ms for UI transitions; 750 ms for data visualisations.

---

## 7. Iconography

All icons use **Lucide React** (`lucide-react@0.554`). Size conventions:

| Context | Size |
|---------|------|
| Navigation icons | `w-4 h-4` |
| Section / card icons | `w-4 h-4` to `w-5 h-5` |
| Feature icons (home grid) | `w-6 h-6` |
| Hero illustration icons | `w-10 h-10` |
| Inline / label icons | `w-3.5 h-3.5` |

Icons are always paired with labels in navigation and CTAs. Icon-only buttons include `title` or `aria-label` attributes.

---

## 8. Responsive Behaviour

| Breakpoint | Behaviour |
|------------|-----------|
| `<640px` (mobile) | Single column; mobile bottom nav with icon + label tabs; icon-only tab fallback in detail panel |
| `640px–1024px` (tablet) | 2-column grids; nav still shows mobile bottom tabs |
| `≥1024px` (desktop) | 12-column diagnostic layout; horizontal nav pills; hero two-column layout |

**Chat widget:** Fixed `width: min(380px, calc(100vw - 48px))` — fits all screen sizes.

---

## 9. Accessibility

| Requirement | Implementation |
|-------------|---------------|
| Keyboard navigation | All buttons, links, and selects are keyboard accessible |
| Focus rings | Browser default retained (not removed) |
| Colour contrast | Text colours pass WCAG AA against their backgrounds |
| Alt text | `alt="Eye scan"` on uploaded image preview |
| ARIA labels | Chat send button, TTS toggle, crop controls |
| Semantic HTML | `<nav>`, `<main>`, `<footer>`, `<button>`, `<label>` used correctly |
| Modal focus trap | Not fully implemented — recommended for future work |

---

## 10. Chat Widget Design

The ChatBot component has its own design language that references the main palette but uses a **darker medical teal** (`#00ADB5`) as its accent and a **deep navy gradient** for the header.

- **FAB colour (closed):** `linear-gradient(135deg, #00adb5, #007a80)`
- **FAB colour (open):** `linear-gradient(135deg, #0f2d4a, #0d4f6e)`
- **Header:** `linear-gradient(135deg, #0d2137, #0d4f6e)`
- **User message bubble:** `linear-gradient(135deg, #0d2137, #0d4f6e)` (dark)
- **Assistant message bubble:** `white` with `border: 1px solid #e2e8f0`
- **Input focus ring:** `border-color: #00adb5`
- **Typing dots:** `bg-teal-400`, 3-dot bouncing animation
