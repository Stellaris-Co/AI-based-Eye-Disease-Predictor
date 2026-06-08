import { useState, useCallback, useEffect, useRef } from 'react'
import axios from 'axios'
import Cropper from 'react-easy-crop'
import getCroppedImg from './cropImage'
import {
  Upload, Activity, AlertTriangle, CheckCircle2,
  ChevronRight, Stethoscope, ShieldAlert, Pill,
  FileText, RefreshCw, Download, MapPin, Eye,
  ScanEye, Volume2, Layers, HelpCircle, ClipboardList,
  ShieldCheck, Microscope, Brain, Info, Github,
  ChevronDown, AlertCircle, VolumeX, Home,
  FlaskConical, GitBranch, BookOpen, Newspaper,
  ExternalLink, Search, Calendar, TrendingUp,
  ArrowRight, Sparkles, X, Send, Loader2, Bot, User,
  MessageCircle, Heart, Zap, Target, BarChart2,
  ChevronLeft, Star, Clock, Tag
} from 'lucide-react'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import ChatBot from './ChatBox'

const ACCENT = '#0891B2'
const ACCENT_DARK = '#0E7490'
const NAVY = '#0F2040'

const urlToBase64 = (url) =>
  new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d').drawImage(img, 0, 0)
      resolve(canvas.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = reject
    img.src = url
  })



const TabButton = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    className={`flex-1 py-3 px-2 flex items-center justify-center gap-1.5 text-xs font-medium transition-all relative border-b-2 whitespace-nowrap
      ${active
        ? 'text-cyan-700 border-cyan-600 bg-cyan-50/40'
        : 'text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-50'
      }`}
  >
    <span className="hidden sm:block">{icon}</span>
    <span className="hidden sm:inline">{label}</span>
    <span className="sm:hidden">{icon}</span>
  </button>
)

const SymptomSelect = ({ label, value, setValue, options }) => (
  <div>
    <label className="block text-[10px] font-semibold text-slate-400 mb-1.5 uppercase tracking-widest">
      {label}
    </label>
    <div className="relative">
      <select
        value={value}
        onChange={e => setValue(e.target.value)}
        className="w-full px-2.5 py-2 text-sm appearance-none rounded-lg text-slate-700"
        style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', fontFamily: 'var(--font-body)' }}
      >
        {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
    </div>
  </div>
)

const ProbabilityBar = ({ label, value }) => {
  const pct = Math.min(100, Math.max(0, value * 100))
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="text-xs font-semibold text-slate-900 tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-1.5 rounded-full prob-bar-fill"
          style={{ width: `${pct}%`, background: pct > 55 ? ACCENT : '#7DD3FC' }}
        />
      </div>
    </div>
  )
}

const SeverityBadge = ({ severity }) => {
  const s = (severity || '').toLowerCase()
  const isHigh = s.includes('high') || s.includes('severe') || s.includes('emergency')
  const isLow = s.includes('low') || s === 'none'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${
      isHigh ? 'bg-red-50 text-red-700'
      : isLow ? 'bg-emerald-50 text-emerald-700'
      : 'bg-amber-50 text-amber-700'
    }`}>
      {severity}
    </span>
  )
}



const HomePage = ({ onNavigate }) => (
  <div className="space-y-0">
    {}
    <section className="relative overflow-hidden bg-white border-b border-slate-200">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full opacity-5"
          style={{ background: `radial-gradient(circle, ${ACCENT}, transparent)` }} />
        <div className="absolute -bottom-20 -left-20 w-64 h-64 rounded-full opacity-5"
          style={{ background: `radial-gradient(circle, ${NAVY}, transparent)` }} />
      </div>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 relative">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="animate-fade-up">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium mb-8"
              style={{ background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 block" />
              AI-Powered Ophthalmic Screening
            </div>
            <h1 className="text-4xl sm:text-5xl font-semibold leading-tight mb-5"
              style={{ color: NAVY, fontFamily: 'var(--font-display)', letterSpacing: '-0.03em' }}>
              Advanced Eye Disease<br />
              <span style={{ color: ACCENT }}>Detection & Analysis</span>
            </h1>
            <p className="text-base text-slate-500 leading-relaxed mb-10 max-w-md">
              Upload a retinal or ocular scan for instant AI screening across 7 conditions using a
              hierarchical deep learning pipeline with Grad-CAM visual explanations.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mb-12">
              <button onClick={() => onNavigate('diagnostic')}
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-semibold text-white text-sm transition-colors"
                style={{ background: ACCENT }}
                onMouseEnter={e => e.currentTarget.style.background = ACCENT_DARK}
                onMouseLeave={e => e.currentTarget.style.background = ACCENT}>
                <ScanEye className="w-4 h-4" /> Start Screening
              </button>
              <button onClick={() => onNavigate('workflow')}
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg font-medium text-sm text-slate-600 transition-colors hover:bg-slate-50"
                style={{ border: '1px solid #E2E8F0' }}>
                How it works <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center gap-8 pt-8 border-t border-slate-100">
              {[
                { value: '7', label: 'Conditions' },
                { value: 'EfficientNet-B4', label: 'Architecture' },
                { value: 'Grad-CAM', label: 'Explainability' },
              ].map((s, i) => (
                <div key={i}>
                  <p className="text-sm font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>{s.value}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="hidden lg:block animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Inference pipeline</p>
            <div className="space-y-1">
              {[
                { step: '01', label: 'Upload Scan', desc: 'JPG · PNG · BMP', icon: <Upload className="w-4 h-4" /> },
                { step: '02', label: 'Router Model', desc: 'MobileNetV3 · 3 anatomical groups', icon: <Brain className="w-4 h-4" /> },
                { step: '03', label: 'Specialist Model', desc: 'EfficientNet-B4 · Fine-grained classification', icon: <Microscope className="w-4 h-4" /> },
                { step: '04', label: 'Diagnosis + Report', desc: 'Grad-CAM heatmap · Clinical advice · PDF export', icon: <FileText className="w-4 h-4" /> },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-white" style={{ border: '1px solid #E2E8F0' }}>
                    <div className="flex items-center justify-center w-8 h-8 rounded-md flex-shrink-0"
                      style={{ background: '#F0F9FF', color: ACCENT }}>
                      {item.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-slate-800">{item.label}</span>
                        <span className="text-[10px] font-semibold text-slate-300 tabular-nums flex-shrink-0">{item.step}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5 truncate">{item.desc}</p>
                    </div>
                  </div>
                  {i < 3 && <div className="flex pl-[18px] py-0.5"><div className="w-px h-4 bg-slate-200" /></div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>

    {}
    <section className="py-12 border-b border-slate-200" style={{ background: '#F8FAFC' }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: <ScanEye className="w-6 h-6" />, title: 'Diagnostic Tool', desc: 'Upload & analyse eye scans', tab: 'diagnostic', color: '#0891B2', bg: '#F0F9FF' },
            { icon: <GitBranch className="w-6 h-6" />, title: 'How It Works', desc: 'AI pipeline & workflow', tab: 'workflow', color: '#7C3AED', bg: '#F5F3FF' },
            { icon: <BookOpen className="w-6 h-6" />, title: 'Conditions', desc: '7 detectable eye diseases', tab: 'conditions', color: '#059669', bg: '#F0FDF4' },
            { icon: <Newspaper className="w-6 h-6" />, title: 'Medical News', desc: 'Latest eye health research', tab: 'news', color: '#DC2626', bg: '#FEF2F2' },
          ].map((card, i) => (
            <button key={i} onClick={() => onNavigate(card.tab)}
              className="flex flex-col items-start p-5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all text-left group">
              <div className="p-2.5 rounded-lg mb-3 transition-colors" style={{ background: card.bg, color: card.color }}>
                {card.icon}
              </div>
              <h3 className="text-sm font-semibold text-slate-800 mb-1">{card.title}</h3>
              <p className="text-xs text-slate-400">{card.desc}</p>
              <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-500 mt-2 transition-colors" />
            </button>
          ))}
        </div>
      </div>
    </section>

    {}
    <section className="py-12 bg-white border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {[
            { icon: <Zap className="w-5 h-5" />, title: 'Instant Analysis', desc: 'Real-time inference in seconds with GPU-accelerated models.', color: '#F59E0B' },
            { icon: <Target className="w-5 h-5" />, title: 'Symptom Cross-Check', desc: 'Rule-based engine validates AI diagnosis against reported symptoms.', color: ACCENT },
            { icon: <Heart className="w-5 h-5" />, title: 'AI Doctor Chat', desc: 'Ophthalmology Q&A powered by Claude or a local LLM.', color: '#EF4444' },
          ].map((f, i) => (
            <div key={i} className="flex items-start gap-4">
              <div className="p-2.5 rounded-lg flex-shrink-0" style={{ background: '#F8FAFC', color: f.color }}>
                {f.icon}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1">{f.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  </div>
)



const WorkflowPage = () => {
  const steps = [
    {
      icon: <Upload className="w-5 h-5" />,
      title: 'Step 1 — Upload Scan',
      desc: 'Upload a high-quality eye scan (JPG, PNG, BMP). Use the built-in crop tool to isolate the region of interest before analysis.',
      detail: 'Accepted formats: JPG, PNG, BMP. Images are pre-processed to 380×380 px before inference.',
      color: '#0891B2',
    },
    {
      icon: <Brain className="w-5 h-5" />,
      title: 'Step 2 — Router Model',
      desc: 'A lightweight MobileNetV3-Large model classifies the scan into one of three anatomical groups: Adnexal/Oculoplastic, Anterior Segment, or Ocular Surface.',
      detail: 'MobileNetV3-Large • 224×224 px input • Adam optimizer • StepLR scheduler',
      color: '#7C3AED',
    },
    {
      icon: <Microscope className="w-5 h-5" />,
      title: 'Step 3 — Specialist Model',
      desc: 'A dedicated EfficientNet-B4 specialist model for the detected anatomical group performs fine-grained disease classification.',
      detail: 'EfficientNet-B4 • 380×380 px • AdamW • CosineAnnealingLR • AMP mixed precision',
      color: '#059669',
    },
    {
      icon: <BarChart2 className="w-5 h-5" />,
      title: 'Step 4 — Symptom Cross-Check',
      desc: 'A rule-based engine cross-validates the AI diagnosis against patient-reported symptoms, surfacing clinical alerts and confirmations.',
      detail: 'Flags dangerous mismatches (e.g. severe pain in conjunctivitis) and confirms supporting symptoms.',
      color: '#F59E0B',
    },
    {
      icon: <ScanEye className="w-5 h-5" />,
      title: 'Step 5 — Grad-CAM Heatmap',
      desc: 'Gradient-weighted Class Activation Mapping generates a visual attention overlay showing which image regions drove the prediction.',
      detail: 'pytorch-grad-cam ≥1.5.4 • Targets last convolutional block of EfficientNet-B4.',
      color: '#EF4444',
    },
    {
      icon: <FileText className="w-5 h-5" />,
      title: 'Step 6 — Report & Advice',
      desc: 'A full clinical report with diagnosis, confidence score, treatment protocol, precautions, and downloadable PDF is generated instantly.',
      detail: 'PDF includes scan + heatmap images, differential diagnosis table, and a "Find Ophthalmologist" QR.',
      color: '#EC4899',
    },
  ]

  const training = [
    { param: 'Architecture (Router)', value: 'MobileNetV3-Large' },
    { param: 'Architecture (Specialists)', value: 'EfficientNet-B4' },
    { param: 'Input size (Router)', value: '224 × 224 px' },
    { param: 'Input size (Specialists)', value: '380 × 380 px' },
    { param: 'Batch size (effective)', value: '32 (4 × 8 gradient accumulation)' },
    { param: 'Optimiser', value: 'AdamW (lr=1e-4, wd=1e-4)' },
    { param: 'Scheduler', value: 'CosineAnnealingLR' },
    { param: 'Epochs', value: '25' },
    { param: 'Mixed Precision', value: 'AMP (specialists only)' },
    { param: 'Class Balancing', value: 'WeightedRandomSampler (5000 samples/class)' },
    { param: 'Pre-training', value: 'ImageNet (DEFAULT weights)' },
  ]

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      <div>
        <p className="section-label mb-2">System Architecture</p>
        <h2 className="text-2xl font-semibold mb-2" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
          Hierarchical Inference Pipeline
        </h2>
        <p className="text-sm text-slate-500 max-w-lg">
          OphthalmoAI mirrors clinical ophthalmology practice: a triage (routing) step precedes subspecialist assessment.
        </p>
      </div>

      {}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {steps.map((s, i) => (
          <div key={i} className="p-5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 transition-colors">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg" style={{ background: s.color + '15', color: s.color }}>{s.icon}</div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Step {String(i + 1).padStart(2, '0')}</span>
            </div>
            <h3 className="text-sm font-semibold mb-1.5" style={{ color: NAVY }}>{s.title}</h3>
            <p className="text-sm text-slate-500 leading-relaxed mb-2">{s.desc}</p>
            <p className="text-[11px] text-slate-400 font-mono bg-slate-50 px-2 py-1 rounded">{s.detail}</p>
          </div>
        ))}
      </div>

      {}
      <div className="rounded-xl bg-slate-900 p-6 overflow-x-auto">
        <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-4">Model hierarchy</p>
        <pre className="text-xs text-cyan-400 font-mono leading-relaxed whitespace-pre">{`Input Image (380×380 px)
        │
        ▼
┌──────────────────────┐
│  Router              │  MobileNetV3-Large (224×224)
│  (3 output classes)  │
└──────────┬───────────┘
           │
     ┌─────┴────────────────────────┐
     │           │                  │
     ▼           ▼                  ▼
 Adnexal    Anterior Segment   Ocular Surface
 (direct)   │                  │
            ├── Cataract        ├── Conjunctivitis
            └── Uveitis         ├── Jaundice
                               ├── Normal
                               └── Pterygium
                    │
          Grad-CAM Heatmap +
          Softmax Probabilities +
          Symptom Cross-Check`}
        </pre>
      </div>

      {}
      <div>
        <h3 className="text-base font-semibold mb-4" style={{ color: NAVY }}>Training Hyperparameters</h3>
        <div className="rounded-xl border border-slate-200 overflow-hidden bg-white">
          {training.map((row, i) => (
            <div key={i} className={`flex items-center justify-between px-5 py-3 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50'} border-b border-slate-100 last:border-0`}>
              <span className="font-medium text-slate-600">{row.param}</span>
              <span className="text-slate-800 font-mono text-xs">{row.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}



const ConditionsPage = () => {
  const [selected, setSelected] = useState(null)

  const conditions = [
    {
      name: 'Cataract', severity: 'Moderate–Severe', color: '#3B82F6', group: 'Anterior Segment',
      desc: 'A progressive clouding of the eye\'s natural lens behind the iris. The leading cause of vision loss worldwide.',
      symptoms: ['Cloudy, blurry, or dim vision', 'Difficulty with night vision', 'Sensitivity to light and glare', 'Halos around lights', 'Fading or yellowing of colors'],
      treatment: ['Prescription glasses (early stage)', 'Phacoemulsification surgery', 'Intraocular Lens (IOL) implantation'],
      precautions: ['UV-blocking sunglasses', 'Quit smoking', 'Manage diabetes', 'Antioxidant-rich diet'],
      advice: 'Surgery is the only effective cure and is highly successful. Consult an ophthalmologist to determine if the cataract is mature enough for removal.',
    },
    {
      name: 'Uveitis', severity: 'High — Sight-Threatening', color: '#EF4444', group: 'Anterior Segment',
      desc: 'Inflammation of the middle layer of the eye (uvea). Often associated with autoimmune disorders or infections.',
      symptoms: ['Deep, boring eye pain', 'Severe redness around iris', 'Extreme light sensitivity (photophobia)', 'Blurred or cloudy vision', 'Floaters'],
      treatment: ['Corticosteroid eye drops', 'Cycloplegic (dilating) drops', 'Oral steroids or immunosuppressives', 'Antiviral/antibiotic if infectious'],
      precautions: ['Dark glasses for light sensitivity', 'Strict steroid drop schedule', 'Screen for autoimmune conditions', 'Monitor eye pressure'],
      advice: 'This is an ocular emergency. Untreated uveitis can lead to glaucoma, cataracts, and blindness. Seek a uveitis specialist immediately.',
    },
    {
      name: 'Conjunctivitis', severity: 'Low (Contagious)', color: '#10B981', group: 'Ocular Surface',
      desc: 'Inflammation of the conjunctiva caused by viruses, bacteria, allergens, or chemical irritants. Commonly called "Pink Eye".',
      symptoms: ['Pink or red in white of eye', 'Itching, irritation, or burning', 'Excessive tearing', 'Thick yellow/green discharge (bacterial)', 'Gritty feeling'],
      treatment: ['Artificial tears', 'Antibiotic eyedrops (bacterial only)', 'Antihistamine drops (allergic)', 'Cold compresses', 'Self-resolves in 7–14 days (viral)'],
      precautions: ['Do not rub eyes', 'Wash hands frequently', 'Change pillowcases daily', 'Discard old eye makeup', 'No contact lenses until healed'],
      advice: 'Practice strict hygiene to prevent spreading. If discharge is thick/yellow or pain is moderate, see a doctor for antibiotics.',
    },
    {
      name: 'Jaundice', severity: 'High — Systemic Emergency', color: '#F59E0B', group: 'Ocular Surface',
      desc: 'Scleral Icterus — yellowing of the eye\'s whites indicating high bilirubin. A vital systemic warning sign, not an eye disease itself.',
      symptoms: ['Yellowing of whites of eyes', 'Yellowing of skin', 'Dark or brown urine', 'Pale, clay-colored stools', 'Fatigue and abdominal pain'],
      treatment: ['Treat underlying cause (liver/gallbladder)', 'Antiviral medication (hepatitis)', 'Surgery for gallstones', 'Alcohol cessation'],
      precautions: ['Avoid alcohol completely', 'No medications without doctor approval', 'Liver-friendly diet', 'Stay hydrated'],
      advice: 'CRITICAL: Seek immediate internal medicine evaluation. Blood tests (LFTs) and ultrasound are needed. Do not ignore this finding.',
    },
    {
      name: 'Pterygium', severity: 'Moderate', color: '#8B5CF6', group: 'Ocular Surface',
      desc: 'A raised, wedge-shaped fibrovascular growth extending from the nasal conjunctiva onto the cornea. Strongly linked to UV exposure.',
      symptoms: ['Pink, fleshy growth on white of eye', 'Foreign body sensation', 'Redness and inflammation', 'Dryness and itching', 'Blurred vision if pupil involved'],
      treatment: ['Lubricating artificial tears', 'Steroid drops (inflammation)', 'Surgical excision with conjunctival autograft', 'Prescription eyewear for astigmatism'],
      precautions: ['Wrap-around UV-blocking sunglasses', 'Wide-brimmed hats outdoors', 'Protect eyes from dust and wind', 'Lubricating drops in dry environments'],
      advice: 'Monitor growth size. If it approaches the pupil or causes persistent irritation, surgical removal is recommended.',
    },
    {
      name: 'Eyelid Conditions', severity: 'Low', color: '#06B6D4', group: 'Adnexal/Oculoplastic',
      desc: 'Covers Hordeolum (Stye), Chalazion, and Blepharitis — inflammatory conditions of the eyelid margin, Meibomian glands, or lash follicles.',
      symptoms: ['Red, painful lump at eyelid edge (Stye)', 'Painless firm lump further back (Chalazion)', 'Greasy flakes at lash base (Blepharitis)', 'Swollen, itchy eyelids', 'Light sensitivity'],
      treatment: ['Warm compresses 10–15 min, 4×/day', 'Eyelid scrubs with baby shampoo', 'Antibiotic ointment / steroid drops', 'Oral doxycycline for chronic blepharitis', 'Surgical drainage if needed'],
      precautions: ['Daily lid hygiene', 'Remove eye makeup before sleep', 'Avoid eyeliner during inflammation', 'Do NOT squeeze or pop styes'],
      advice: 'Consistency with warm compresses is key. Most styes/chalazia resolve with heat therapy. Seek care if vision is affected or lid becomes very hot.',
    },
    {
      name: 'Normal', severity: 'None', color: '#22C55E', group: 'All Groups',
      desc: 'No visible anterior segment pathology detected. The eye appears structurally normal with healthy conjunctiva, cornea, iris, and pupil.',
      symptoms: ['No pain, redness, or discharge', 'Clear vision', 'No light sensitivity'],
      treatment: ['No medical treatment required', 'Routine maintenance'],
      precautions: ['UV-protective sunglasses', '20-20-20 rule for digital eyestrain', 'Protective eyewear during sports', 'Diet rich in Omega-3 and Vitamin A', 'Avoid smoking'],
      advice: 'Your eyes look healthy! Continue scheduling comprehensive eye exams every 1–2 years to detect conditions not visible externally.',
    },
  ]

  const ConditionCard = ({ c }) => (
    <div className="p-5 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all cursor-pointer"
      onClick={() => setSelected(c)}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-2.5 h-2.5 rounded-full" style={{ background: c.color }} />
        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{c.group}</span>
      </div>
      <h3 className="text-sm font-semibold mb-1" style={{ color: NAVY }}>{c.name}</h3>
      <p className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-2">{c.desc}</p>
      <div className="flex items-center justify-between">
        <SeverityBadge severity={c.severity} />
        <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
      </div>
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <p className="section-label mb-2">Coverage</p>
        <h2 className="text-2xl font-semibold mb-2" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
          7 Conditions, 3 Anatomical Groups
        </h2>
        <p className="text-sm text-slate-500 max-w-lg">
          Click any condition card for detailed clinical information, symptoms, treatment protocols, and precautions.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {conditions.map((c, i) => <ConditionCard key={i} c={c} />)}
      </div>

      {}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,32,64,0.7)', backdropFilter: 'blur(4px)' }}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between p-6 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: selected.color }} />
                <div>
                  <h2 className="text-xl font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>{selected.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-400">{selected.group}</span>
                    <span className="text-slate-200">·</span>
                    <SeverityBadge severity={selected.severity} />
                  </div>
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>
            <div className="p-6 space-y-5">
              <p className="text-sm text-slate-600 leading-relaxed">{selected.desc}</p>
              {[
                { label: 'Common Symptoms', items: selected.symptoms, icon: <Activity className="w-3.5 h-3.5" />, color: ACCENT },
                { label: 'Treatment Options', items: selected.treatment, icon: <Pill className="w-3.5 h-3.5" />, color: '#059669' },
                { label: 'Precautions', items: selected.precautions, icon: <ShieldCheck className="w-3.5 h-3.5" />, color: '#7C3AED' },
              ].map((section, i) => (
                <div key={i}>
                  <div className="flex items-center gap-2 mb-2.5">
                    <span style={{ color: section.color }}>{section.icon}</span>
                    <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400">{section.label}</h4>
                  </div>
                  <div className="space-y-1.5">
                    {section.items.map((item, j) => (
                      <div key={j} className="flex items-start gap-2.5 text-sm text-slate-600">
                        <div className="w-1 h-1 rounded-full flex-shrink-0 mt-2" style={{ background: section.color }} />
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              <div className="p-4 rounded-lg border border-cyan-100" style={{ background: '#F0F9FF' }}>
                <div className="flex items-center gap-2 mb-1.5">
                  <Stethoscope className="w-3.5 h-3.5" style={{ color: ACCENT }} />
                  <span className="text-xs font-semibold" style={{ color: '#0369A1' }}>Clinical Note</span>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">{selected.advice}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}



const MedicalNewsPage = () => {
  const [activeCategory, setActiveCategory] = useState('All')

  const categories = ['All', 'Research', 'Technology', 'Prevention', 'Treatment', 'Pediatric']

  const news = [
    {
      title: 'AI Outperforms Junior Doctors in Diagnosing Diabetic Retinopathy from Fundus Photos',
      category: 'Technology', date: 'May 2025', readTime: '5 min',
      summary: 'A multi-center study published in Nature Medicine demonstrated that a deep learning model achieved 94.5% sensitivity and 91.2% specificity in detecting referable diabetic retinopathy — outperforming three junior ophthalmologists under time-pressure conditions.',
      tags: ['AI', 'Diabetic Retinopathy', 'Deep Learning'],
      highlight: true,
      source: 'Nature Medicine',
    },
    {
      title: 'Omega-3 Fatty Acids Linked to 20% Reduction in Age-Related Macular Degeneration Risk',
      category: 'Prevention', date: 'April 2025', readTime: '4 min',
      summary: 'A 12-year longitudinal cohort study (n=38,000) found that participants with the highest dietary intake of DHA and EPA had a significantly lower incidence of early AMD compared to those with the lowest intake.',
      tags: ['AMD', 'Nutrition', 'Prevention'],
      highlight: false,
      source: 'JAMA Ophthalmology',
    },
    {
      title: 'Gene Therapy Trial Shows 70% Vision Improvement in Leber Congenital Amaurosis Patients',
      category: 'Treatment', date: 'April 2025', readTime: '6 min',
      summary: 'Phase III clinical trial results for AAV-mediated RPE65 gene therapy showed durable visual improvements at 3-year follow-up, with 70% of treated eyes meeting the primary endpoint of clinically meaningful functional vision improvement.',
      tags: ['Gene Therapy', 'LCA', 'Rare Disease'],
      highlight: false,
      source: 'The Lancet',
    },
    {
      title: 'Smartphone-Based OCT Reaches Primary Care — A Game Changer for Glaucoma Screening',
      category: 'Technology', date: 'March 2025', readTime: '4 min',
      summary: 'A portable, smartphone-attachable OCT device priced under $500 demonstrated 88% sensitivity for detecting glaucomatous optic nerve changes in a real-world primary care setting, opening the door to widespread community screening.',
      tags: ['Glaucoma', 'OCT', 'Telemedicine'],
      highlight: false,
      source: 'British Journal of Ophthalmology',
    },
    {
      title: 'Blue Light from Screens: Myth vs. Reality — A 2025 Meta-Analysis',
      category: 'Research', date: 'March 2025', readTime: '7 min',
      summary: 'A comprehensive meta-analysis of 64 studies found no strong evidence linking screen-emitted blue light to permanent retinal damage in healthy adults. However, circadian rhythm disruption from evening screen use remains a well-supported concern.',
      tags: ['Blue Light', 'Digital Eye Strain', 'Meta-Analysis'],
      highlight: false,
      source: 'Investigative Ophthalmology & Visual Science',
    },
    {
      title: 'Global Myopia Crisis: 50% of World\'s Population Expected to Be Myopic by 2050',
      category: 'Research', date: 'February 2025', readTime: '5 min',
      summary: 'Updated modelling using global prevalence data projects that approximately 4.8 billion people will be myopic by 2050, with high myopia (≥−6D) affecting nearly 1 billion. Outdoor time and low-dose atropine remain the most evidence-backed interventions.',
      tags: ['Myopia', 'Epidemiology', 'Public Health'],
      highlight: true,
      source: 'The Lancet',
    },
    {
      title: 'Children\'s Vision After COVID-19: Screen Time and the Accelerated Myopia Surge',
      category: 'Pediatric', date: 'February 2025', readTime: '4 min',
      summary: 'Post-pandemic data from 12 Asian countries show a 2–3× acceleration in myopia progression among school-age children. The WHO recommends at least 2 hours of outdoor time daily as a primary preventative strategy.',
      tags: ['Myopia', 'Pediatric', 'COVID-19'],
      highlight: false,
      source: 'WHO Global Report',
    },
    {
      title: 'FDA Approves First Drop-Based Treatment for Presbyopia in Adults Over 40',
      category: 'Treatment', date: 'January 2025', readTime: '3 min',
      summary: 'A once-daily pilocarpine 1.25% ophthalmic solution received FDA approval for treating age-related near-vision blur. Clinical trials showed 30% of patients achieved ≥3 lines of improvement in corrected distance visual acuity.',
      tags: ['Presbyopia', 'FDA Approval', 'Treatment'],
      highlight: false,
      source: 'FDA Press Release',
    },
  ]

  const filtered = activeCategory === 'All' ? news : news.filter(n => n.category === activeCategory)

  const categoryColors = {
    Research: { bg: '#EDE9FE', text: '#6D28D9' },
    Technology: { bg: '#DBEAFE', text: '#1D4ED8' },
    Prevention: { bg: '#D1FAE5', text: '#065F46' },
    Treatment: { bg: '#FEE2E2', text: '#B91C1C' },
    Pediatric: { bg: '#FEF3C7', text: '#92400E' },
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <p className="section-label mb-2">Latest Research</p>
        <h2 className="text-2xl font-semibold mb-2" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
          Eye Health & Ophthalmology News
        </h2>
        <p className="text-sm text-slate-500 max-w-lg">
          Curated highlights from peer-reviewed journals and major ophthalmology publications.
        </p>
      </div>

      {}
      <div className="flex flex-wrap gap-2 mb-8">
        {categories.map(cat => (
          <button key={cat} onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              activeCategory === cat
                ? 'text-white'
                : 'bg-white border border-slate-200 text-slate-500 hover:border-slate-300'
            }`}
            style={activeCategory === cat ? { background: ACCENT } : {}}>
            {cat}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {filtered.map((article, i) => {
          const catStyle = categoryColors[article.category] || { bg: '#F1F5F9', text: '#475569' }
          return (
            <div key={i}
              className={`rounded-xl bg-white border overflow-hidden hover:shadow-md transition-all ${
                article.highlight ? 'border-cyan-200' : 'border-slate-200'
              }`}>
              {article.highlight && (
                <div className="flex items-center gap-1.5 px-5 py-2 border-b border-cyan-100" style={{ background: '#F0F9FF' }}>
                  <Star className="w-3 h-3 fill-current" style={{ color: ACCENT }} />
                  <span className="text-xs font-semibold" style={{ color: ACCENT }}>Featured Study</span>
                </div>
              )}
              <div className="p-5">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded-full" style={{ background: catStyle.bg, color: catStyle.text }}>
                    {article.category}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-slate-400">
                    <Calendar className="w-3 h-3" /> {article.date}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-slate-400">
                    <Clock className="w-3 h-3" /> {article.readTime} read
                  </span>
                  <span className="text-xs text-slate-300 italic">{article.source}</span>
                </div>
                <h3 className="text-sm font-semibold mb-2 leading-snug" style={{ color: NAVY }}>{article.title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed mb-3">{article.summary}</p>
                <div className="flex flex-wrap items-center gap-2">
                  {article.tags.map((tag, j) => (
                    <span key={j} className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-50 border border-slate-200 text-slate-500">
                      <Tag className="w-2.5 h-2.5" /> {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-8 p-4 rounded-xl border border-amber-200 bg-amber-50">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#D97706' }} />
          <p className="text-xs text-amber-700">
            <strong>Note:</strong> These articles are curated summaries for educational purposes. Always consult the original peer-reviewed publications and qualified healthcare professionals for medical decisions. OphthalmoAI is not responsible for the accuracy of third-party research summaries.
          </p>
        </div>
      </div>
    </div>
  )
}



const DiagnosticPage = () => {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('treatment')
  const [showHeatmap, setShowHeatmap] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  const [pain, setPain] = useState('None')
  const [vision, setVision] = useState('No')
  const [itch, setItch] = useState('No')
  const [halos, setHalos] = useState('No')
  const [discharge, setDischarge] = useState('None')
  const [lightSens, setLightSens] = useState('No')
  const [spots, setSpots] = useState('No')
  const [duration, setDuration] = useState('Not Sure')

  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null)
  const [isCropping, setIsCropping] = useState(false)

  useEffect(() => () => window.speechSynthesis.cancel(), [])

  const onCropComplete = useCallback((_, cap) => setCroppedAreaPixels(cap), [])

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setIsCropping(true)
    setResult(null)
    setHeatmap(null)
    setShowHeatmap(false)
  }

  const handleCropConfirm = async () => {
    try {
      const cropped = await getCroppedImg(preview, croppedAreaPixels)
      setPreview(URL.createObjectURL(cropped))
      setFile(cropped)
      setIsCropping(false)
    } catch (e) { console.error(e) }
  }

  const handleAnalyze = async () => {
    if (!file) return
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('pain', pain)
    formData.append('vision', vision)
    formData.append('itch', itch)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const { data } = await axios.post(`${apiUrl}/predict`, formData)
      if (data.error) throw new Error(data.error)
      setResult(data)
      setHeatmap(data.heatmap || null)
      setActiveTab('treatment')
    } catch (err) {
      alert(`Analysis Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const resetApp = () => {
    setFile(null); setPreview(null); setResult(null); setHeatmap(null)
    setShowHeatmap(false); setIsCropping(false)
    setPain('None'); setVision('No'); setItch('No')
    setHalos('No'); setDischarge('None'); setLightSens('No'); setSpots('No')
    window.speechSynthesis.cancel(); setIsSpeaking(false)
  }

  const speakReport = () => {
    if (!result) return
    if (isSpeaking) { window.speechSynthesis.cancel(); setIsSpeaking(false); return }
    const utt = new SpeechSynthesisUtterance(
      `Diagnosis: ${result.diagnosis}. Confidence: ${result.confidence.toFixed(0)} percent. ${result.details.advice}`
    )
    utt.onend = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utt)
    setIsSpeaking(true)
  }

  const downloadPDF = async () => {
    if (!result) return
    const doc = new jsPDF()
    const brand = [15, 32, 64]
    const accent = [8, 145, 178]
    const lightBg = [240, 249, 255]
    const pageW = 210

    const addHeader = (title, pageNum, totalPages) => {
      doc.setFillColor(...brand)
      doc.rect(0, 0, pageW, 28, 'F')
      doc.setFillColor(...accent)
      doc.rect(0, 26, pageW, 2, 'F')
      
      doc.setTextColor(255, 255, 255)
      doc.setFontSize(15); doc.setFont('helvetica', 'bold')
      doc.text('OphthalmoAI', 14, 13)
      doc.setFontSize(8); doc.setFont('helvetica', 'normal')
      doc.setTextColor(160, 210, 230)
      doc.text('AI-Powered Ophthalmic Screening Report', 14, 20)
      doc.setTextColor(255, 255, 255)
      doc.setFontSize(8)
      doc.text(title, pageW - 14, 12, { align: 'right' })
      doc.text(`Generated: ${new Date().toLocaleString()}`, pageW - 14, 19, { align: 'right' })
      doc.text(`Page ${pageNum} of ${totalPages}`, pageW - 14, 26, { align: 'right' })
    }

    const addFooter = () => {
      doc.setFillColor(248, 250, 252)
      doc.rect(0, 280, pageW, 17, 'F')
      doc.setDrawColor(226, 232, 240)
      doc.line(0, 280, pageW, 280)
      doc.setTextColor(150); doc.setFontSize(6.5)
      doc.text('⚕ MEDICAL DISCLAIMER: OphthalmoAI is a research and educational screening tool. It is NOT a substitute for professional medical diagnosis, advice, or treatment.', 14, 285)
      doc.text('Always consult a qualified ophthalmologist for clinical decisions. This report is generated by an AI model and may contain errors.', 14, 290)
    }

    const sectionTitle = (text, y) => {
      doc.setFillColor(...lightBg)
      doc.rect(14, y - 4, pageW - 28, 10, 'F')
      doc.setDrawColor(...accent)
      doc.rect(14, y - 4, 3, 10, 'F')
      doc.setFontSize(9); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
      doc.text(text, 20, y + 2)
      return y + 10
    }

    
    addHeader('Clinical Summary — Page 1', 1, 4)

    
    const isCritical = (result.details.severity || '').toLowerCase().includes('high') || (result.details.severity || '').toLowerCase().includes('emergency')
    const isNormal = result.diagnosis === 'Normal'
    const bannerColor = isNormal ? [16, 185, 129] : isCritical ? [220, 38, 38] : [...accent]
    doc.setFillColor(...bannerColor)
    doc.roundedRect(14, 35, pageW - 28, 42, 3, 3, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(22); doc.setFont('helvetica', 'bold')
    doc.text(result.diagnosis.toUpperCase(), 22, 54)
    doc.setFontSize(9); doc.setFont('helvetica', 'normal')
    doc.text(`AI Confidence: ${result.confidence.toFixed(1)}%`, 22, 63)
    doc.text(`Severity: ${result.details.severity}`, 22, 70)
    doc.text(`Anatomical Group: ${result.group_name}`, 90, 63)
    doc.text(`Analysis Date: ${new Date().toLocaleDateString()}`, 90, 70)

    
    let y = 86
    if (result.hybrid_warnings?.length > 0) {
      y = sectionTitle('⚠ AI Clinical Alerts', y)
      doc.setFillColor(255, 251, 235)
      doc.roundedRect(14, y, pageW - 28, result.hybrid_warnings.length * 7 + 8, 2, 2, 'F')
      doc.setDrawColor(245, 158, 11)
      doc.roundedRect(14, y, pageW - 28, result.hybrid_warnings.length * 7 + 8, 2, 2, 'S')
      doc.setTextColor(146, 64, 14); doc.setFontSize(8); doc.setFont('helvetica', 'normal')
      result.hybrid_warnings.forEach((w, i) => {
        doc.text(`• ${w}`, 18, y + 6 + i * 7)
      })
      y += result.hybrid_warnings.length * 7 + 14
    }

    
    y = sectionTitle('Patient-Reported Symptoms', y)
    autoTable(doc, {
      startY: y,
      head: [['Symptom', 'Patient Response']],
      body: [
        ['Pain Level', pain],
        ['Vision Blurry / Reduced', vision],
        ['Itchiness', itch],
        ['Halos or Glare', halos],
        ['Eye Discharge', discharge],
        ['Light Sensitivity (Photophobia)', lightSens],
        ['Floaters / Dark Spots', spots],
        ['Duration of Symptoms', duration],
      ],
      theme: 'grid',
      headStyles: { fillColor: brand, fontSize: 8, fontStyle: 'bold' },
      bodyStyles: { fontSize: 8 },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { fontStyle: 'bold', cellWidth: 75 } },
      margin: { left: 14, right: 14 },
    })

    addFooter()

    
    doc.addPage()
    addHeader('Diagnostic Imaging — Page 2', 2, 4)

    y = 40
    y = sectionTitle('Patient Scan & AI Attention Heatmap (Grad-CAM)', y)

    try {
      let imgLoaded = 0
      if (preview) {
        const b64 = await urlToBase64(preview)
        doc.addImage(b64, 'JPEG', 14, y, 85, 85)
        doc.setTextColor(100); doc.setFontSize(7)
        doc.text('Original Patient Scan', 56, y + 88, { align: 'center' })
        imgLoaded++
      }
      if (heatmap) {
        doc.addImage(heatmap, 'JPEG', 112, y, 85, 85)
        doc.setTextColor(100); doc.setFontSize(7)
        doc.text('AI Attention Heatmap (Grad-CAM)', 154, y + 88, { align: 'center' })
        imgLoaded++
      }
      y += 98
      if (imgLoaded === 0) {
        doc.setTextColor(150); doc.setFontSize(9)
        doc.text('No images available for this scan.', 105, y, { align: 'center' })
        y += 15
      }
    } catch (e) {
      console.warn('PDF image error:', e)
      y += 15
    }

    
    y = sectionTitle('About Grad-CAM Visualisation', y)
    doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.setTextColor(80)
    const gradCamText = 'Gradient-weighted Class Activation Mapping (Grad-CAM) highlights the image regions that most influenced the AI\'s prediction. Red/warm areas indicate high attention — these are the features the model considers most diagnostically relevant. This transparency tool helps clinicians validate or question AI findings.'
    const gcLines = doc.splitTextToSize(gradCamText, pageW - 28)
    doc.text(gcLines, 14, y)
    y += gcLines.length * 5 + 10

    
    y = sectionTitle('Differential Diagnosis — AI Confidence Distribution', y)
    const probs = Object.entries(result.probabilities || {}).sort(([, a], [, b]) => b - a)
    const barMaxW = 100
    probs.forEach(([label, prob], i) => {
      const pct = prob * 100
      const barW = (pct / 100) * barMaxW
      const barY = y + i * 14
      doc.setFillColor(226, 232, 240)
      doc.roundedRect(60, barY, barMaxW, 7, 1, 1, 'F')
      const rgb = pct > 55 ? accent : [125, 211, 252]
      doc.setFillColor(...rgb)
      doc.roundedRect(60, barY, barW, 7, 1, 1, 'F')
      doc.setFontSize(7.5); doc.setFont('helvetica', i === 0 ? 'bold' : 'normal'); doc.setTextColor(...brand)
      doc.text(label.replace(/_/g, ' '), 14, barY + 5.5)
      doc.setFont('helvetica', 'bold'); doc.setTextColor(50)
      doc.text(`${pct.toFixed(1)}%`, 165, barY + 5.5)
    })

    addFooter()

    
    doc.addPage()
    addHeader('Clinical Analysis — Page 3', 3, 4)

    y = 40
    y = sectionTitle('Condition Overview', y)
    doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.setTextColor(60)
    const descLines = doc.splitTextToSize(result.details.description || 'No description available.', pageW - 28)
    doc.text(descLines, 14, y)
    y += descLines.length * 4.5 + 8

    if (result.details.analysis) {
      y = sectionTitle('Visual Analysis Notes', y)
      doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.setTextColor(60)
      const anaLines = doc.splitTextToSize(result.details.analysis, pageW - 28)
      doc.text(anaLines, 14, y)
      y += anaLines.length * 4.5 + 8
    }

    y = sectionTitle('Clinical Recommendation', y)
    doc.setFillColor(...lightBg)
    doc.roundedRect(14, y, pageW - 28, 20, 2, 2, 'F')
    doc.setFontSize(8.5); doc.setFont('helvetica', 'bold'); doc.setTextColor(...accent)
    const advLines = doc.splitTextToSize(result.details.advice || 'Please consult an ophthalmologist.', pageW - 34)
    doc.text(advLines, 17, y + 7)
    y += 28

    y = sectionTitle('Treatment Protocol', y)
    autoTable(doc, {
      startY: y,
      head: [['#', 'Recommended Treatment / Intervention']],
      body: (result.details.treatment || []).map((t, i) => [String(i + 1), t]),
      theme: 'striped',
      headStyles: { fillColor: brand, fontSize: 8 },
      bodyStyles: { fontSize: 8 },
      columnStyles: { 0: { cellWidth: 10, halign: 'center' } },
      margin: { left: 14, right: 14 },
    })

    y = doc.lastAutoTable.finalY + 8
    y = sectionTitle('Common Symptoms of This Condition', y)
    autoTable(doc, {
      startY: y,
      head: [['Symptom']],
      body: (result.details.symptoms || []).map(s => [s]),
      theme: 'striped',
      headStyles: { fillColor: [70, 70, 70], fontSize: 8 },
      bodyStyles: { fontSize: 8 },
      margin: { left: 14, right: 14 },
    })

    addFooter()

    
    doc.addPage()
    addHeader('Precautions & Next Steps — Page 4', 4, 4)

    y = 40
    y = sectionTitle('Precautions & Self-Care', y)
    autoTable(doc, {
      startY: y,
      head: [['#', 'Precaution']],
      body: (result.details.precautions || []).map((p, i) => [String(i + 1), p]),
      theme: 'striped',
      headStyles: { fillColor: [109, 40, 217], fontSize: 8 },
      bodyStyles: { fontSize: 8 },
      columnStyles: { 0: { cellWidth: 10, halign: 'center' } },
      margin: { left: 14, right: 14 },
    })

    y = doc.lastAutoTable.finalY + 10

    
    y = sectionTitle('🗺 Find a Qualified Ophthalmologist Near You', y)
    doc.setFillColor(240, 253, 244)
    doc.roundedRect(14, y, pageW - 28, 55, 3, 3, 'F')
    doc.setDrawColor(16, 185, 129)
    doc.roundedRect(14, y, pageW - 28, 55, 3, 3, 'S')

    doc.setFontSize(9); doc.setFont('helvetica', 'bold'); doc.setTextColor(6, 78, 59)
    doc.text('How to find the nearest ophthalmologist:', 18, y + 9)

    const searchLinks = [
      { label: 'Google Maps Search', url: 'https://www.google.com/maps/search/ophthalmologist+near+me' },
      { label: 'Practo (India)', url: 'https://www.practo.com/find-doctors/eye-doctor-ophthalmologist' },
      { label: 'Healthgrades (US)', url: 'https://www.healthgrades.com/ophthalmologist-directory' },
      { label: 'NHS Find a Service (UK)', url: 'https://www.nhs.uk/nhs-services/opticians' },
    ]
    doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.setTextColor(6, 95, 70)
    searchLinks.forEach((link, i) => {
      doc.text(`• ${link.label}: ${link.url}`, 18, y + 18 + i * 9)
    })

    doc.setFontSize(7.5); doc.setTextColor(100)
    doc.text('* These links are provided for convenience. OphthalmoAI is not affiliated with any of these services.', 18, y + 52)

    y += 65

    
    y = sectionTitle('🚨 When to Seek Immediate Emergency Eye Care', y)
    const emergencies = [
      'Sudden loss of vision in one or both eyes',
      'Eye injury from chemical splash or foreign object',
      'Sudden severe eye pain with nausea/vomiting',
      'Double vision or visual disturbances after head trauma',
      'Curtain/shadow effect in visual field (possible retinal detachment)',
      'Yellow sclera (jaundice) — seek internal medicine immediately',
    ]
    doc.setFillColor(254, 242, 242)
    doc.roundedRect(14, y, pageW - 28, emergencies.length * 7.5 + 10, 2, 2, 'F')
    doc.setDrawColor(220, 38, 38)
    doc.roundedRect(14, y, pageW - 28, emergencies.length * 7.5 + 10, 2, 2, 'S')
    doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.setTextColor(185, 28, 28)
    emergencies.forEach((e, i) => {
      doc.text(`⚡ ${e}`, 18, y + 7 + i * 7.5)
    })

    addFooter()

    const ts = new Date().toISOString().slice(0, 19).replace(/[: ]/g, '-')
    doc.save(`OphthalmoAI_Report_${result.diagnosis}_${ts}.pdf`)
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {}
      {isCropping && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center p-4"
          style={{ background: 'rgba(15, 32, 64, 0.95)' }}>
          <p className="text-white/50 text-xs mb-4 uppercase tracking-widest font-medium">Adjust crop area</p>
          <div className="relative w-full max-w-sm overflow-hidden rounded-xl"
            style={{ height: 'min(52vh, 360px)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <Cropper image={preview} crop={crop} zoom={zoom} aspect={1}
              onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={onCropComplete} />
          </div>
          <div className="flex w-full max-w-sm gap-3 mt-4">
            <button onClick={() => { setIsCropping(false); setFile(null); setPreview(null) }}
              className="flex-1 py-2.5 text-sm font-medium rounded-lg transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#94A3B8', border: '1px solid rgba(255,255,255,0.08)' }}>
              Cancel
            </button>
            <button onClick={handleCropConfirm}
              className="flex-1 py-2.5 text-sm font-semibold text-white rounded-lg"
              style={{ background: ACCENT }}>
              Confirm &amp; Continue
            </button>
          </div>
          <p className="flex items-center gap-1.5 mt-3 text-xs text-slate-500">
            <ScanEye className="w-3.5 h-3.5" /> Pinch or scroll to zoom · Drag to reposition
          </p>
        </div>
      )}

      <div className="mb-8">
        <p className="section-label mb-2">Diagnostic Tool</p>
        <h2 className="text-2xl font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
          Upload a Scan to Begin
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            {!preview ? (
              <label className="flex flex-col items-center justify-center h-52 cursor-pointer border-b border-dashed border-slate-200 transition-colors hover:bg-slate-50">
                <div className="p-3 rounded-xl mb-3" style={{ background: '#F0F9FF' }}>
                  <Upload className="w-6 h-6" style={{ color: ACCENT }} />
                </div>
                <span className="text-sm font-medium text-slate-600">Upload Eye Scan</span>
                <span className="mt-1 text-xs text-slate-400">JPG · PNG · BMP</span>
                <input type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
              </label>
            ) : (
              <div className="relative bg-slate-900 h-52 overflow-hidden group">
                <img src={showHeatmap && heatmap ? heatmap : preview} className="object-contain w-full h-full" alt="Eye scan" />
                {heatmap && (
                  <div className="absolute inset-0 flex items-end p-3 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/50 to-transparent">
                    <button onClick={() => setShowHeatmap(!showHeatmap)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-white text-xs font-medium"
                      style={{ background: 'rgba(8, 145, 178, 0.85)' }}>
                      {showHeatmap ? <Eye className="w-3.5 h-3.5" /> : <ScanEye className="w-3.5 h-3.5" />}
                      {showHeatmap ? 'Original Scan' : 'AI Heatmap'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {preview && !result && (
              <div className="p-5 border-b border-slate-100 animate-fade-in">
                <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Symptom Assessment</h3>
                <div className="grid grid-cols-2 gap-3 stagger">
                  <SymptomSelect label="Pain Level" value={pain} setValue={setPain} options={['None', 'Mild', 'Severe', 'Not Sure']} />
                  <SymptomSelect label="Vision Blurry?" value={vision} setValue={setVision} options={['No', 'Yes', 'Not Sure']} />
                  <SymptomSelect label="Itchy?" value={itch} setValue={setItch} options={['No', 'Yes', 'Not Sure']} />
                  <SymptomSelect label="Discharge?" value={discharge} setValue={setDischarge} options={['None', 'Watery', 'Thick/Yellow', 'Not Sure']} />
                  <SymptomSelect label="Halos / Glare?" value={halos} setValue={setHalos} options={['No', 'Yes', 'Not Sure']} />
                  <SymptomSelect label="Light Sensitive?" value={lightSens} setValue={setLightSens} options={['No', 'Yes', 'Not Sure']} />
                  <SymptomSelect label="Floaters / Spots?" value={spots} setValue={setSpots} options={['No', 'Yes', 'Not Sure']} />
                  <SymptomSelect label="Duration?" value={duration} setValue={setDuration} options={['<1 day', '1–3 days', '4–7 days', '1–4 weeks', '>1 month', 'Not Sure']} />
                </div>
              </div>
            )}

            <div className="p-4 flex flex-col gap-2.5">
              <button onClick={handleAnalyze} disabled={!file || loading}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm text-white transition-colors"
                style={{ background: (!file || loading) ? '#94A3B8' : ACCENT, cursor: loading ? 'wait' : (!file ? 'not-allowed' : 'pointer') }}
                onMouseEnter={e => { if (!loading && file) e.currentTarget.style.background = ACCENT_DARK }}
                onMouseLeave={e => { if (!loading && file) e.currentTarget.style.background = ACCENT }}>
                {loading ? <><RefreshCw className="w-4 h-4 animate-spin" /> Analysing scan…</> : <>Run AI Diagnosis</>}
              </button>
              {result && (
                <button onClick={resetApp}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium text-slate-500 transition-colors hover:bg-slate-50"
                  style={{ border: '1px solid #E2E8F0' }}>
                  <RefreshCw className="w-3.5 h-3.5" /> New Scan
                </button>
              )}
            </div>
          </div>

          {!result && (
            <div className="grid grid-cols-3 gap-3">
              {[{ label: '7 Conditions', sub: 'Detected' }, { label: 'EfficientNet-B4', sub: 'Backbone' }, { label: 'Grad-CAM', sub: 'Heatmaps' }].map((c, i) => (
                <div key={i} className="flex flex-col items-center gap-1 py-4 rounded-xl text-center bg-white" style={{ border: '1px solid #E2E8F0' }}>
                  <span className="text-xs font-semibold" style={{ color: NAVY }}>{c.label}</span>
                  <span className="text-[10px] text-slate-400">{c.sub}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {}
        <div className="lg:col-span-7">
          {result ? (
            <div className="space-y-4 animate-fade-up">
              {}
              <div className="rounded-xl bg-white overflow-hidden"
                style={{ border: '1px solid #E2E8F0', borderLeft: `4px solid ${result.diagnosis === 'Normal' ? '#10B981' : ACCENT}` }}>
                <div className="p-6 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2.5 rounded-xl flex-shrink-0 mt-0.5"
                      style={{ background: result.diagnosis === 'Normal' ? '#F0FDF4' : '#F0F9FF' }}>
                      {result.diagnosis === 'Normal'
                        ? <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        : <AlertTriangle className="w-5 h-5" style={{ color: ACCENT }} />}
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">Screening Result</p>
                      <h2 className="text-2xl font-semibold tracking-tight" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
                        {result.diagnosis.replace(/_/g, ' ')}
                      </h2>
                      <div className="flex flex-wrap items-center gap-2 mt-2.5">
                        <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-md"
                          style={{ background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD' }}>
                          {result.confidence.toFixed(1)}% confidence
                        </span>
                        <span className="inline-flex items-center text-xs text-slate-500 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200">
                          {result.group_name}
                        </span>
                        <SeverityBadge severity={result.details.severity} />
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button onClick={speakReport}
                      className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                      title={isSpeaking ? 'Stop narration' : 'Read report aloud'}>
                      {isSpeaking ? <VolumeX className="w-4 h-4" style={{ color: ACCENT }} /> : <Volume2 className="w-4 h-4 text-slate-400" />}
                    </button>
                    <button onClick={downloadPDF}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-xs font-medium text-slate-500"
                      title="Download 4-page PDF report">
                      <Download className="w-4 h-4" /> PDF Report
                    </button>
                  </div>
                </div>
              </div>

              {}
              {result.hybrid_warnings?.length > 0 && (
                <div className="flex items-start gap-3 p-4 rounded-xl animate-fade-in"
                  style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderLeft: '4px solid #F59E0B' }}>
                  <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#D97706' }} />
                  <div>
                    <p className="text-xs font-semibold mb-1.5" style={{ color: '#92400E' }}>Clinical Alerts</p>
                    {result.hybrid_warnings.map((w, i) => (
                      <p key={i} className="text-sm leading-snug" style={{ color: '#B45309' }}>• {w}</p>
                    ))}
                  </div>
                </div>
              )}

              {}
              <div className="rounded-xl bg-white border border-slate-200 overflow-hidden">
                <div className="flex border-b border-slate-100">
                  <TabButton active={activeTab === 'treatment'} onClick={() => setActiveTab('treatment')} icon={<Pill className="w-3.5 h-3.5" />} label="Treatment" />
                  <TabButton active={activeTab === 'doctor'} onClick={() => setActiveTab('doctor')} icon={<Stethoscope className="w-3.5 h-3.5" />} label="Doctor's Note" />
                  <TabButton active={activeTab === 'symptoms'} onClick={() => setActiveTab('symptoms')} icon={<ClipboardList className="w-3.5 h-3.5" />} label="Symptoms" />
                  <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')} icon={<Layers className="w-3.5 h-3.5" />} label="AI Stats" />
                </div>

                <div className="p-5 sm:p-6 min-h-[260px]">
                  {activeTab === 'treatment' && (
                    <div className="space-y-4 animate-fade-in">
                      <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Treatment Protocol</h4>
                      <div className="space-y-2">
                        {(result.details.treatment || []).map((t, i) => (
                          <div key={i} className="flex items-start gap-3 p-3.5 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                            <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" style={{ background: ACCENT }} />
                            <p className="text-sm text-slate-700 leading-snug">{t}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeTab === 'doctor' && (
                    <div className="space-y-4 animate-fade-in">
                      <div className="p-4 rounded-lg border" style={{ background: '#F0F9FF', borderColor: '#BAE6FD' }}>
                        <div className="flex items-center gap-2 mb-2">
                          <Stethoscope className="w-3.5 h-3.5" style={{ color: ACCENT }} />
                          <span className="text-xs font-semibold" style={{ color: '#0369A1' }}>Clinical Note</span>
                        </div>
                        <p className="text-sm text-slate-700 leading-relaxed">{result.details.advice}</p>
                      </div>
                      <div className="p-4 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-2">Condition Overview</p>
                        <p className="text-sm text-slate-600 leading-relaxed">{result.details.description}</p>
                      </div>
                      {result.details.analysis && (
                        <div className="p-4 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-2">Visual Analysis</p>
                          <p className="text-sm text-slate-600 leading-relaxed">{result.details.analysis}</p>
                        </div>
                      )}
                      <a href="https://www.google.com/maps/search/ophthalmologist+near+me" target="_blank" rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2 w-full py-3 rounded-lg text-sm font-medium transition-colors text-white"
                        style={{ background: NAVY }}
                        onMouseEnter={e => e.currentTarget.style.background = '#1E3A5F'}
                        onMouseLeave={e => e.currentTarget.style.background = NAVY}>
                        <MapPin className="w-4 h-4" /> Find Nearest Ophthalmologist
                      </a>
                    </div>
                  )}

                  {activeTab === 'symptoms' && (
                    <div className="animate-fade-in">
                      <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">Common Indicators — {result.diagnosis}</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-5">
                        {(result.details.symptoms || []).map((s, i) => (
                          <div key={i} className="flex items-center gap-2.5 p-3 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: ACCENT }} />
                            <span className="text-sm text-slate-700">{s}</span>
                          </div>
                        ))}
                      </div>
                      {result.details.precautions?.length > 0 && (
                        <>
                          <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-3">Precautions</h4>
                          <div className="space-y-2">
                            {result.details.precautions.map((p, i) => (
                              <div key={i} className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: '#F0F9FF', border: '1px solid #BAE6FD' }}>
                                <ShieldCheck className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: ACCENT }} />
                                <span className="text-sm text-slate-600">{p}</span>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {activeTab === 'stats' && (
                    <div className="space-y-5 animate-fade-in">
                      <div>
                        <h4 className="text-sm font-semibold mb-0.5" style={{ color: NAVY }}>Differential Diagnosis</h4>
                        <p className="text-xs text-slate-400">Confidence within the <em>{result.group_name}</em> specialist</p>
                      </div>
                      <div className="space-y-3.5">
                        {Object.entries(result.probabilities || {})
                          .sort(([, a], [, b]) => b - a)
                          .map(([label, prob], i) => <ProbabilityBar key={i} label={label.replace(/_/g, ' ')} value={prob} />)}
                      </div>
                      <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                        Probabilities reflect AI confidence within the detected anatomical group, not absolute clinical certainty.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white">
              <div className="p-5 rounded-2xl mb-4" style={{ background: '#F0F9FF' }}>
                <Eye className="w-10 h-10" style={{ color: '#BAE6FD' }} />
              </div>
              <p className="text-sm font-semibold text-slate-400 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Ready for Analysis</p>
              <p className="text-xs text-slate-300 mb-6">Upload an eye scan to begin</p>
              <div className="flex flex-wrap justify-center gap-1.5 px-6">
                {['Cataract', 'Conjunctivitis', 'Uveitis', 'Pterygium', 'Eyelid', 'Jaundice', 'Normal'].map(c => (
                  <span key={c} className="text-[10px] px-2.5 py-1 rounded-md font-medium"
                    style={{ background: '#F0F9FF', color: '#7DD3FC', border: '1px solid #E0F2FE' }}>
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {}
      <ChatBot diagnosisContext={result} />
    </div>
  )
}



const DisclaimerBanner = () => (
  <div className="py-2.5 border-b border-amber-100" style={{ background: '#FFFBEB' }}>
    <div className="max-w-6xl mx-auto px-4 flex items-center justify-center gap-2">
      <Info className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#D97706' }} />
      <p className="text-xs" style={{ color: '#92400E' }}>
        <strong>Medical Disclaimer:</strong> OphthalmoAI is a research and educational screening tool.
        Not a substitute for professional medical diagnosis. Always consult a qualified ophthalmologist.
      </p>
    </div>
  </div>
)

const Footer = () => (
  <footer className="py-8 border-t border-slate-200" style={{ background: '#F8FAFC' }}>
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <Eye className="w-4 h-4" style={{ color: ACCENT }} />
        <span className="text-sm font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
          Ophthalmo<span style={{ color: ACCENT }}>AI</span>
        </span>
        <span className="text-slate-200 text-sm select-none">·</span>
        <span className="text-xs text-slate-400">AI-Powered Ophthalmic Screening</span>
      </div>
      <div className="flex items-center gap-5 text-xs text-slate-400">
        <a href="https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1.5 hover:text-slate-700 transition-colors">
          <Github className="w-3.5 h-3.5" /> Source Code
        </a>
        <span>© 2025 · MIT License</span>
      </div>
    </div>
  </footer>
)



const NAV_TABS = [
  { id: 'home', label: 'Home', icon: <Home className="w-4 h-4" /> },
  { id: 'diagnostic', label: 'Diagnostic', icon: <ScanEye className="w-4 h-4" /> },
  { id: 'workflow', label: 'How It Works', icon: <GitBranch className="w-4 h-4" /> },
  { id: 'conditions', label: 'Conditions', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'news', label: 'Medical News', icon: <Newspaper className="w-4 h-4" /> },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('home')

  const tabLabel = NAV_TABS.find(t => t.id === activeTab)?.label || 'Home'

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)', fontFamily: 'var(--font-body)' }}>

      {}
      <nav className="sticky top-0 z-40 bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {}
            <button onClick={() => setActiveTab('home')} className="flex items-center gap-2.5">
              <div className="flex items-center justify-center w-7 h-7 rounded-md" style={{ background: '#F0F9FF' }}>
                <Eye className="w-4 h-4" style={{ color: ACCENT }} />
              </div>
              <span className="text-sm font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
                Ophthalmo<span style={{ color: ACCENT }}>AI</span>
              </span>
            </button>

            {}
            <div className="hidden md:flex items-center gap-1">
              {NAV_TABS.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'text-cyan-700 bg-cyan-50'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                  }`}>
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            {}
            <div className="flex items-center gap-3">
              <span className="md:hidden text-xs font-medium text-slate-500">{tabLabel}</span>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 block" />
                <span className="hidden sm:block text-xs font-medium text-slate-500">System Active</span>
              </div>
            </div>
          </div>

          {}
          <div className="flex md:hidden border-t border-slate-100 -mx-4 px-2">
            {NAV_TABS.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex flex-col items-center gap-0.5 py-2 text-[9px] font-medium transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? 'text-cyan-700 border-cyan-600'
                    : 'text-slate-400 border-transparent'
                }`}>
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      <DisclaimerBanner />

      {}
      <main>
        {activeTab === 'home' && <HomePage onNavigate={setActiveTab} />}
        {activeTab === 'diagnostic' && <DiagnosticPage />}
        {activeTab === 'workflow' && <WorkflowPage />}
        {activeTab === 'conditions' && <ConditionsPage />}
        {activeTab === 'news' && <MedicalNewsPage />}
      </main>

      <Footer />
    </div>
  )
}
