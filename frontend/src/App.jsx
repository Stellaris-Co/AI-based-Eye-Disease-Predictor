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
  ChevronDown, AlertCircle, VolumeX
} from 'lucide-react'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import ChatBot from './ChatBox'


const ACCENT      = '#0891B2'
const ACCENT_DARK = '#0E7490'
const NAVY        = '#0F2040'


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
        style={{
          background: '#FFFFFF',
          border: '1px solid #E2E8F0',
          fontFamily: 'var(--font-body)',
        }}
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
  const isLow  = s.includes('low') || s === 'none'
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


const HeroSection = ({ onStartScan }) => (
  <section className="bg-white border-b border-slate-200">
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

        
        <div className="animate-fade-up">
          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium mb-8"
            style={{ background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD' }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 block" />
            AI-Powered Ophthalmic Screening
          </div>

          <h1
            className="text-4xl sm:text-[2.75rem] font-semibold leading-tight mb-5"
            style={{ color: NAVY, fontFamily: 'var(--font-display)', letterSpacing: '-0.03em' }}
          >
            Advanced Eye Disease Detection
          </h1>

          <p className="text-base text-slate-500 leading-relaxed mb-10 max-w-md">
            Upload a retinal or ocular scan for instant AI screening across 7 conditions using a
            hierarchical deep learning pipeline with Grad-CAM visual explanations.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 mb-12">
            <button
              onClick={onStartScan}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-white text-sm transition-colors"
              style={{ background: ACCENT, fontFamily: 'var(--font-body)' }}
              onMouseEnter={e => e.currentTarget.style.background = ACCENT_DARK}
              onMouseLeave={e => e.currentTarget.style.background = ACCENT}
            >
              <ScanEye className="w-4 h-4" />
              Start Screening
            </button>
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm text-slate-600 transition-colors hover:text-slate-900 hover:bg-slate-50"
              style={{ border: '1px solid #E2E8F0' }}
            >
              How it works
            </a>
          </div>

          <div className="flex items-center gap-8 pt-8 border-t border-slate-100">
            {[
              { value: '7', label: 'Conditions' },
              { value: 'EfficientNet-B4', label: 'Architecture' },
              { value: 'Grad-CAM', label: 'Explainability' },
            ].map((s, i) => (
              <div key={i}>
                <p className="text-sm font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
                  {s.value}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        
        <div className="hidden lg:block animate-fade-up" style={{ animationDelay: '0.1s' }}>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">
            Inference pipeline
          </p>
          <div className="space-y-1">
            {[
              { step: '01', label: 'Upload Scan', desc: 'JPG · PNG · BMP', icon: <Upload className="w-4 h-4" /> },
              { step: '02', label: 'Router Model', desc: 'MobileNetV3 · 3 anatomical groups', icon: <Brain className="w-4 h-4" /> },
              { step: '03', label: 'Specialist Model', desc: 'EfficientNet-B4 · Fine-grained classification', icon: <Microscope className="w-4 h-4" /> },
              { step: '04', label: 'Diagnosis + Report', desc: 'Grad-CAM heatmap · Clinical advice · PDF export', icon: <FileText className="w-4 h-4" /> },
            ].map((item, i) => (
              <div key={i}>
                <div
                  className="flex items-center gap-3 p-3 rounded-lg bg-white"
                  style={{ border: '1px solid #E2E8F0' }}
                >
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-md flex-shrink-0"
                    style={{ background: '#F0F9FF', color: ACCENT }}
                  >
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
                {i < 3 && (
                  <div className="flex pl-[18px] py-0.5">
                    <div className="w-px h-4 bg-slate-200" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  </section>
)


const HowItWorksSection = () => {
  const steps = [
    {
      icon: <Upload className="w-5 h-5" />,
      title: 'Upload Scan',
      desc: 'Upload a high-quality eye scan. Use the built-in crop tool to isolate the region of interest before analysis.',
    },
    {
      icon: <Brain className="w-5 h-5" />,
      title: 'AI Analysis',
      desc: 'A lightweight MobileNetV3 router routes the scan to the correct EfficientNet-B4 specialist model.',
    },
    {
      icon: <FileText className="w-5 h-5" />,
      title: 'Clinical Report',
      desc: 'Receive a diagnosis with confidence score, Grad-CAM heatmap, treatment protocol, and a downloadable PDF.',
    },
  ]

  return (
    <section id="how-it-works" className="py-16 sm:py-20 border-b border-slate-200" style={{ background: '#F8FAFC' }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-10">
          <p className="section-label mb-2">Workflow</p>
          <h2 className="text-2xl font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
            How OphthalmoAI Works
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {steps.map((s, i) => (
            <div key={i} className="p-6 rounded-xl bg-white border border-slate-200">
              <div className="flex items-center gap-3 mb-5">
                <div className="p-2 rounded-lg" style={{ background: '#F0F9FF', color: ACCENT }}>
                  {s.icon}
                </div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Step {String(i + 1).padStart(2, '0')}
                </span>
              </div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: NAVY }}>{s.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}


const ConditionsSection = () => {
  const conditions = [
    { name: 'Cataract',          severity: 'Moderate–Severe', color: '#3B82F6', group: 'Anterior',       desc: 'Clouding of the crystalline lens.' },
    { name: 'Uveitis',           severity: 'High',            color: '#EF4444', group: 'Anterior',       desc: 'Uveal tract inflammation, often autoimmune.' },
    { name: 'Conjunctivitis',    severity: 'Low',             color: '#10B981', group: 'Ocular Surface', desc: 'Viral, bacterial, or allergic conjunctival inflammation.' },
    { name: 'Jaundice',          severity: 'High — Systemic', color: '#F59E0B', group: 'Ocular Surface', desc: 'Scleral icterus indicating elevated bilirubin.' },
    { name: 'Pterygium',         severity: 'Moderate',        color: '#8B5CF6', group: 'Ocular Surface', desc: 'Fibrovascular growth extending onto the cornea.' },
    { name: 'Eyelid Conditions', severity: 'Low',             color: '#06B6D4', group: 'Adnexal',        desc: 'Stye, chalazion, and blepharitis.' },
    { name: 'Normal',            severity: 'None',            color: '#22C55E', group: 'All Groups',     desc: 'No visible anterior segment pathology.' },
  ]

  return (
    <section className="py-16 sm:py-20 bg-white border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-10">
          <p className="section-label mb-2">Coverage</p>
          <h2 className="text-2xl font-semibold mb-2" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
            7 Conditions, 3 Anatomical Groups
          </h2>
          <p className="text-sm text-slate-500 max-w-lg">
            A hierarchical model first routes the scan to the correct anatomical specialist,
            then performs fine-grained disease classification.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {conditions.map((c, i) => (
            <div
              key={i}
              className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors cursor-default"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{c.group}</span>
              </div>
              <h3 className="text-sm font-semibold mb-1" style={{ color: NAVY }}>{c.name}</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">{c.desc}</p>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded ${
                c.severity.toLowerCase().includes('high')
                  ? 'bg-red-50 text-red-600'
                  : c.severity === 'None' || c.severity === 'Low'
                  ? 'bg-emerald-50 text-emerald-600'
                  : 'bg-amber-50 text-amber-600'
              }`}>
                {c.severity}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}


const DisclaimerBanner = () => (
  <div className="py-2.5 border-b border-amber-100" style={{ background: '#FFFBEB' }}>
    <div className="max-w-6xl mx-auto px-4 flex items-center justify-center gap-2">
      <Info className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#D97706' }} />
      <p className="text-xs" style={{ color: '#92400E' }}>
        <strong>Medical Disclaimer:</strong> OphthalmoAI is a research and educational screening tool.
        It is not a substitute for professional medical diagnosis. Always consult a qualified ophthalmologist.
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
        <a
          href="https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 hover:text-slate-700 transition-colors"
        >
          <Github className="w-3.5 h-3.5" />
          Source Code
        </a>
        <span>© 2025 · MIT License</span>
      </div>
    </div>
  </footer>
)


export default function App() {
  const [file, setFile]             = useState(null)
  const [preview, setPreview]       = useState(null)
  const [heatmap, setHeatmap]       = useState(null)
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState(null)
  const [activeTab, setActiveTab]   = useState('treatment')
  const [showHeatmap, setShowHeatmap]   = useState(false)
  const [isSpeaking, setIsSpeaking]     = useState(false)

  
  const [pain, setPain]           = useState('None')
  const [vision, setVision]       = useState('No')
  const [itch, setItch]           = useState('No')
  const [halos, setHalos]         = useState('No')
  const [discharge, setDischarge] = useState('None')
  const [lightSens, setLightSens] = useState('No')
  const [spots, setSpots]         = useState('No')

  
  const [crop, setCrop]                           = useState({ x: 0, y: 0 })
  const [zoom, setZoom]                           = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null)
  const [isCropping, setIsCropping]               = useState(false)

  const diagnosticRef = useRef(null)

  useEffect(() => () => window.speechSynthesis.cancel(), [])

  const onCropComplete = useCallback((_, cap) => setCroppedAreaPixels(cap), [])

  const scrollToDiagnostic = () =>
    diagnosticRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

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
    const brand  = [15, 32, 64]
    const accent = [8, 145, 178]
    const lightBg = [240, 249, 255]

    const addHeader = (title) => {
      doc.setFillColor(...brand)
      doc.rect(0, 0, 210, 26, 'F')
      doc.setFillColor(...accent)
      doc.rect(0, 24, 210, 2, 'F')
      doc.setTextColor(255, 255, 255)
      doc.setFontSize(14); doc.setFont('helvetica', 'bold')
      doc.text('OphthalmoAI Diagnostics', 14, 16)
      doc.setFontSize(8); doc.setFont('helvetica', 'normal')
      doc.text(title, 196, 10, { align: 'right' })
      doc.text(`${new Date().toLocaleDateString()}`, 196, 17, { align: 'right' })
    }

    const addFooter = (pg) => {
      doc.setTextColor(150); doc.setFontSize(7)
      doc.text('For educational screening only. Not a substitute for professional medical diagnosis.', 105, 287, { align: 'center' })
      doc.text(`Page ${pg}`, 196, 287, { align: 'right' })
    }

    
    addHeader('Patient Report')
    doc.setFillColor(...lightBg)
    doc.roundedRect(14, 33, 182, 36, 3, 3, 'F')
    doc.setFillColor(...accent)
    doc.roundedRect(14, 33, 4, 36, 1, 1, 'F')
    doc.setFontSize(18); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text(result.diagnosis.toUpperCase(), 24, 48)
    doc.setFontSize(9); doc.setFont('helvetica', 'normal'); doc.setTextColor(80)
    doc.text(`Confidence: ${result.confidence.toFixed(1)}%  ·  ${result.details.severity}  ·  ${result.group_name}`, 24, 60)

    doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text('1. Reported Symptoms', 14, 80)
    autoTable(doc, {
      startY: 84,
      head: [['Symptom', 'Response']],
      body: [
        ['Pain Level', pain], ['Vision Blurry?', vision], ['Itchiness', itch],
        ['Halos / Glare', halos], ['Discharge', discharge],
        ['Light Sensitivity', lightSens], ['Floaters / Spots', spots]
      ],
      theme: 'grid',
      headStyles: { fillColor: brand, fontSize: 8 },
      bodyStyles: { fontSize: 8 },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: { 0: { fontStyle: 'bold', cellWidth: 55 } }
    })

    const imgY = doc.lastAutoTable.finalY + 10
    doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text('2. Diagnostic Imaging', 14, imgY)
    try {
      if (preview) {
        const b64 = await urlToBase64(preview)
        doc.addImage(b64, 'JPEG', 14, imgY + 4, 78, 78)
        doc.setFontSize(7); doc.setTextColor(120)
        doc.text('Patient Scan', 53, imgY + 86, { align: 'center' })
      }
      if (heatmap) {
        doc.addImage(heatmap, 'JPEG', 112, imgY + 4, 78, 78)
        doc.setFontSize(7); doc.setTextColor(120)
        doc.text('AI Attention Heatmap (Grad-CAM)', 151, imgY + 86, { align: 'center' })
      }
    } catch (e) { console.warn('PDF image error:', e) }
    addFooter(1)

    
    doc.addPage(); addHeader('Clinical Analysis')
    doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text('3. Condition Overview', 14, 38)
    doc.setFont('helvetica', 'normal'); doc.setFontSize(8); doc.setTextColor(60)
    const descLines = doc.splitTextToSize(result.details.description || '', 182)
    doc.text(descLines, 14, 46)

    const advY = 46 + descLines.length * 4.5 + 6
    doc.setFontSize(9); doc.setFont('helvetica', 'bold'); doc.setTextColor(...accent)
    doc.text("Clinical Note:", 14, advY)
    doc.setFont('helvetica', 'normal'); doc.setFontSize(8); doc.setTextColor(60)
    const advLines = doc.splitTextToSize(result.details.advice || '', 182)
    doc.text(advLines, 14, advY + 6)

    const treatY = advY + 6 + advLines.length * 4.5 + 8
    doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text('4. Treatment Protocol', 14, treatY)
    autoTable(doc, {
      startY: treatY + 4,
      head: [['Recommended Treatments']],
      body: (result.details.treatment || []).map(t => [`• ${t}`]),
      theme: 'striped', headStyles: { fillColor: brand }, bodyStyles: { fontSize: 8 }
    })

    doc.setFontSize(10); doc.setFont('helvetica', 'bold'); doc.setTextColor(...brand)
    doc.text('5. Differential Diagnosis', 14, doc.lastAutoTable.finalY + 10)
    autoTable(doc, {
      startY: doc.lastAutoTable.finalY + 14,
      head: [['Condition', 'AI Confidence']],
      body: Object.entries(result.probabilities || {})
        .sort(([, a], [, b]) => b - a)
        .map(([l, p]) => [l.replace(/_/g, ' '), `${(p * 100).toFixed(1)}%`]),
      theme: 'striped', headStyles: { fillColor: [70, 70, 70] }, bodyStyles: { fontSize: 8 },
      columnStyles: { 1: { halign: 'right', fontStyle: 'bold' } }
    })
    addFooter(2)

    const ts = new Date().toISOString().slice(0, 19).replace(/[: ]/g, '-')
    doc.save(`OphthalmoAI_${result.diagnosis}_${ts}.pdf`)
  }

  
  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)', fontFamily: 'var(--font-body)' }}>

      
      {isCropping && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center p-4"
          style={{ background: 'rgba(15, 32, 64, 0.95)' }}>
          <p className="text-white/50 text-xs mb-4 uppercase tracking-widest font-medium">
            Adjust crop area
          </p>
          <div
            className="relative w-full max-w-sm overflow-hidden rounded-xl"
            style={{ height: 'min(52vh, 360px)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <Cropper
              image={preview} crop={crop} zoom={zoom} aspect={1}
              onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={onCropComplete}
            />
          </div>
          <div className="flex w-full max-w-sm gap-3 mt-4">
            <button
              onClick={() => { setIsCropping(false); setFile(null); setPreview(null) }}
              className="flex-1 py-2.5 text-sm font-medium rounded-lg transition-colors"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#94A3B8', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              Cancel
            </button>
            <button
              onClick={handleCropConfirm}
              className="flex-1 py-2.5 text-sm font-semibold text-white rounded-lg transition-colors"
              style={{ background: ACCENT }}
              onMouseEnter={e => e.currentTarget.style.background = ACCENT_DARK}
              onMouseLeave={e => e.currentTarget.style.background = ACCENT}
            >
              Confirm &amp; Continue
            </button>
          </div>
          <p className="flex items-center gap-1.5 mt-3 text-xs text-slate-500">
            <ScanEye className="w-3.5 h-3.5" /> Pinch or scroll to zoom · Drag to reposition
          </p>
        </div>
      )}

      
      <nav className="sticky top-0 z-40 bg-white border-b border-slate-200">
        <div className="flex items-center justify-between h-14 px-4 mx-auto max-w-6xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-2.5">
            <div
              className="flex items-center justify-center w-7 h-7 rounded-md"
              style={{ background: '#F0F9FF' }}
            >
              <Eye className="w-4 h-4" style={{ color: ACCENT }} />
            </div>
            <div>
              <span className="text-sm font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
                Ophthalmo<span style={{ color: ACCENT }}>AI</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-5">
            <a href="#how-it-works" className="hidden sm:block text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors">
              How it works
            </a>
            <a href="#conditions" className="hidden sm:block text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors">
              Conditions
            </a>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 block" />
              <span className="text-xs font-medium text-slate-500">System Active</span>
            </div>
          </div>
        </div>
      </nav>

      
      <HeroSection onStartScan={scrollToDiagnostic} />

      
      <DisclaimerBanner />

      
      <section ref={diagnosticRef} id="diagnostic" className="py-12 sm:py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-10">
            <p className="section-label mb-2">Diagnostic Tool</p>
            <h2 className="text-2xl font-semibold" style={{ color: NAVY, fontFamily: 'var(--font-display)' }}>
              Upload a Scan to Begin
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">

            
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">

                
                {!preview ? (
                  <label
                    className="flex flex-col items-center justify-center h-52 cursor-pointer border-b border-dashed border-slate-200 transition-colors hover:bg-slate-50 group"
                  >
                    <div className="p-3 rounded-xl mb-3 transition-colors" style={{ background: '#F0F9FF' }}>
                      <Upload className="w-6 h-6" style={{ color: ACCENT }} />
                    </div>
                    <span className="text-sm font-medium text-slate-600">Upload Eye Scan</span>
                    <span className="mt-1 text-xs text-slate-400">JPG · PNG · BMP</span>
                    <input type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                  </label>
                ) : (
                  <div className="relative bg-slate-900 h-52 overflow-hidden group">
                    <img
                      src={showHeatmap && heatmap ? heatmap : preview}
                      className="object-contain w-full h-full"
                      alt="Eye scan"
                    />
                    {heatmap && (
                      <div className="absolute inset-0 flex items-end p-3 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/50 to-transparent">
                        <button
                          onClick={() => setShowHeatmap(!showHeatmap)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-white text-xs font-medium"
                          style={{ background: 'rgba(8, 145, 178, 0.85)', backdropFilter: 'blur(4px)' }}
                        >
                          {showHeatmap ? <Eye className="w-3.5 h-3.5" /> : <ScanEye className="w-3.5 h-3.5" />}
                          {showHeatmap ? 'Original Scan' : 'AI Heatmap'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                
                {preview && !result && (
                  <div className="p-5 border-b border-slate-100 animate-fade-in">
                    <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">
                      Symptom Assessment
                    </h3>
                    <div className="grid grid-cols-2 gap-3 stagger">
                      <SymptomSelect label="Pain Level"       value={pain}      setValue={setPain}      options={['None', 'Mild', 'Severe', 'Not Sure']} />
                      <SymptomSelect label="Vision Blurry?"   value={vision}    setValue={setVision}    options={['No', 'Yes', 'Not Sure']} />
                      <SymptomSelect label="Itchy?"           value={itch}      setValue={setItch}      options={['No', 'Yes', 'Not Sure']} />
                      <SymptomSelect label="Discharge?"       value={discharge} setValue={setDischarge} options={['None', 'Watery', 'Thick/Yellow', 'Not Sure']} />
                      <SymptomSelect label="Halos / Glare?"   value={halos}     setValue={setHalos}     options={['No', 'Yes', 'Not Sure']} />
                      <SymptomSelect label="Light Sensitive?" value={lightSens} setValue={setLightSens} options={['No', 'Yes', 'Not Sure']} />
                      <div className="col-span-2">
                        <SymptomSelect label="Floaters / Spots?" value={spots} setValue={setSpots} options={['No', 'Yes', 'Not Sure']} />
                      </div>
                    </div>
                  </div>
                )}

                
                <div className="p-4 flex flex-col gap-2.5">
                  <button
                    onClick={handleAnalyze}
                    disabled={!file || loading}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm text-white transition-colors"
                    style={{
                      background: (!file || loading) ? '#94A3B8' : ACCENT,
                      cursor: loading ? 'wait' : (!file ? 'not-allowed' : 'pointer'),
                      fontFamily: 'var(--font-body)',
                    }}
                    onMouseEnter={e => { if (!loading && file) e.currentTarget.style.background = ACCENT_DARK }}
                    onMouseLeave={e => { if (!loading && file) e.currentTarget.style.background = ACCENT }}
                  >
                    {loading ? (
                      <><RefreshCw className="w-4 h-4 animate-spin" /> Analysing scan…</>
                    ) : (
                      <>Run AI Diagnosis</>
                    )}
                  </button>
                  {result && (
                    <button
                      onClick={resetApp}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium text-slate-500 transition-colors hover:text-slate-700 hover:bg-slate-50"
                      style={{ border: '1px solid #E2E8F0' }}
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> New Scan
                    </button>
                  )}
                </div>
              </div>

              
              {!result && (
                <div className="grid grid-cols-3 gap-3 animate-fade-up">
                  {[
                    { label: '7 Conditions', sub: 'Detected' },
                    { label: 'EfficientNet-B4', sub: 'Backbone' },
                    { label: 'Grad-CAM', sub: 'Heatmaps' },
                  ].map((c, i) => (
                    <div
                      key={i}
                      className="flex flex-col items-center gap-1 py-4 rounded-xl text-center bg-white"
                      style={{ border: '1px solid #E2E8F0' }}
                    >
                      <span className="text-xs font-semibold" style={{ color: NAVY }}>{c.label}</span>
                      <span className="text-[10px] text-slate-400">{c.sub}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            
            <div className="lg:col-span-7">
              {result ? (
                <div className="space-y-4 animate-fade-up">

                  
                  <div
                    className="rounded-xl bg-white overflow-hidden"
                    style={{ border: '1px solid #E2E8F0', borderLeft: `4px solid ${result.diagnosis === 'Normal' ? '#10B981' : ACCENT}` }}
                  >
                    <div className="p-6 flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div
                          className="p-2.5 rounded-xl flex-shrink-0 mt-0.5"
                          style={{ background: result.diagnosis === 'Normal' ? '#F0FDF4' : '#F0F9FF' }}
                        >
                          {result.diagnosis === 'Normal'
                            ? <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                            : <AlertTriangle className="w-5 h-5" style={{ color: ACCENT }} />}
                        </div>
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
                            Screening Result
                          </p>
                          <h2
                            className="text-2xl font-semibold tracking-tight"
                            style={{ color: NAVY, fontFamily: 'var(--font-display)' }}
                          >
                            {result.diagnosis.replace(/_/g, ' ')}
                          </h2>
                          <div className="flex flex-wrap items-center gap-2 mt-2.5">
                            <span
                              className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-md"
                              style={{ background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD' }}
                            >
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
                        <button
                          onClick={speakReport}
                          className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                          title={isSpeaking ? 'Stop narration' : 'Read report aloud'}
                        >
                          {isSpeaking
                            ? <VolumeX className="w-4 h-4" style={{ color: ACCENT }} />
                            : <Volume2 className="w-4 h-4 text-slate-400" />}
                        </button>
                        <button
                          onClick={downloadPDF}
                          className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                          title="Download PDF report"
                        >
                          <Download className="w-4 h-4 text-slate-400" />
                        </button>
                      </div>
                    </div>
                  </div>

                  
                  {result.hybrid_warnings?.length > 0 && (
                    <div
                      className="flex items-start gap-3 p-4 rounded-xl animate-fade-in"
                      style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderLeft: '4px solid #F59E0B' }}
                    >
                      <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#D97706' }} />
                      <div>
                        <p className="text-xs font-semibold mb-1.5" style={{ color: '#92400E' }}>Clinical Alerts</p>
                        {result.hybrid_warnings.map((w, i) => (
                          <p key={i} className="text-sm leading-snug" style={{ color: '#B45309' }}>• {w}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  
                  <div className="rounded-xl bg-white border border-slate-200 overflow-hidden">
                    
                    <div className="flex border-b border-slate-100">
                      <TabButton active={activeTab === 'treatment'} onClick={() => setActiveTab('treatment')}
                        icon={<Pill className="w-3.5 h-3.5" />} label="Treatment" />
                      <TabButton active={activeTab === 'doctor'} onClick={() => setActiveTab('doctor')}
                        icon={<Stethoscope className="w-3.5 h-3.5" />} label="Doctor's Note" />
                      <TabButton active={activeTab === 'symptoms'} onClick={() => setActiveTab('symptoms')}
                        icon={<ClipboardList className="w-3.5 h-3.5" />} label="Symptoms" />
                      <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')}
                        icon={<Layers className="w-3.5 h-3.5" />} label="AI Stats" />
                    </div>

                    
                    <div className="p-5 sm:p-6 min-h-[260px]">

                      {activeTab === 'treatment' && (
                        <div className="space-y-4 animate-fade-in">
                          <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
                            Treatment Protocol
                          </h4>
                          <div className="space-y-2">
                            {(result.details.treatment || []).map((t, i) => (
                              <div
                                key={i}
                                className="flex items-start gap-3 p-3.5 rounded-lg border border-slate-100 hover:border-slate-200 transition-colors"
                                style={{ background: '#FAFBFC' }}
                              >
                                <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" style={{ background: ACCENT }} />
                                <p className="text-sm text-slate-700 leading-snug">{t}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {activeTab === 'doctor' && (
                        <div className="space-y-4 animate-fade-in">
                          <div
                            className="p-4 rounded-lg border"
                            style={{ background: '#F0F9FF', borderColor: '#BAE6FD' }}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Stethoscope className="w-3.5 h-3.5" style={{ color: ACCENT }} />
                              <span className="text-xs font-semibold" style={{ color: '#0369A1' }}>Clinical Note</span>
                            </div>
                            <p className="text-sm text-slate-700 leading-relaxed">{result.details.advice}</p>
                          </div>
                          <div className="p-4 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-2">
                              Condition Overview
                            </p>
                            <p className="text-sm text-slate-600 leading-relaxed">{result.details.description}</p>
                          </div>
                          {result.details.analysis && (
                            <div className="p-4 rounded-lg border border-slate-100" style={{ background: '#FAFBFC' }}>
                              <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-2">
                                Visual Analysis
                              </p>
                              <p className="text-sm text-slate-600 leading-relaxed">{result.details.analysis}</p>
                            </div>
                          )}
                          <a
                            href="https://www.google.com/maps/search/ophthalmologist+near+me"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 w-full py-3 rounded-lg text-sm font-medium transition-colors text-white"
                            style={{ background: NAVY }}
                            onMouseEnter={e => e.currentTarget.style.background = '#1E3A5F'}
                            onMouseLeave={e => e.currentTarget.style.background = NAVY}
                          >
                            <MapPin className="w-4 h-4" /> Find Nearest Ophthalmologist
                          </a>
                        </div>
                      )}

                      {activeTab === 'symptoms' && (
                        <div className="animate-fade-in">
                          <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-4">
                            Common Indicators — {result.diagnosis}
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-5">
                            {(result.details.symptoms || []).map((s, i) => (
                              <div
                                key={i}
                                className="flex items-center gap-2.5 p-3 rounded-lg border border-slate-100"
                                style={{ background: '#FAFBFC' }}
                              >
                                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: ACCENT }} />
                                <span className="text-sm text-slate-700">{s}</span>
                              </div>
                            ))}
                          </div>
                          {result.details.precautions?.length > 0 && (
                            <>
                              <h4 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-3">
                                Precautions
                              </h4>
                              <div className="space-y-2">
                                {result.details.precautions.map((p, i) => (
                                  <div
                                    key={i}
                                    className="flex items-start gap-2.5 p-3 rounded-lg"
                                    style={{ background: '#F0F9FF', border: '1px solid #BAE6FD' }}
                                  >
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
                            <p className="text-xs text-slate-400">
                              Confidence distribution within the <em>{result.group_name}</em> specialist model
                            </p>
                          </div>
                          <div className="space-y-3.5">
                            {Object.entries(result.probabilities || {})
                              .sort(([, a], [, b]) => b - a)
                              .map(([label, prob], i) => (
                                <ProbabilityBar key={i} label={label.replace(/_/g, ' ')} value={prob} />
                              ))}
                          </div>
                          <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                            Probabilities reflect AI model confidence within the detected anatomical group, not absolute clinical certainty.
                          </p>
                        </div>
                      )}

                    </div>
                  </div>

                </div>
              ) : (
                
                <div
                  className="h-full min-h-[400px] flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200"
                  style={{ background: 'white' }}
                >
                  <div
                    className="p-5 rounded-2xl mb-4"
                    style={{ background: '#F0F9FF' }}
                  >
                    <Eye className="w-10 h-10" style={{ color: '#BAE6FD' }} />
                  </div>
                  <p className="text-sm font-semibold text-slate-400 mb-1" style={{ fontFamily: 'var(--font-display)' }}>
                    Ready for Analysis
                  </p>
                  <p className="text-xs text-slate-300 mb-6">Upload an eye scan to begin</p>
                  <div className="flex flex-wrap justify-center gap-1.5 px-6">
                    {['Cataract', 'Conjunctivitis', 'Uveitis', 'Pterygium', 'Eyelid', 'Jaundice', 'Normal'].map(c => (
                      <span
                        key={c}
                        className="text-[10px] px-2.5 py-1 rounded-md font-medium"
                        style={{ background: '#F0F9FF', color: '#7DD3FC', border: '1px solid #E0F2FE' }}
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </section>

      
      <HowItWorksSection />

      
      <section id="conditions">
        <ConditionsSection />
      </section>

      
      <Footer />

      
      <ChatBot diagnosisContext={result} />

    </div>
  )
}
