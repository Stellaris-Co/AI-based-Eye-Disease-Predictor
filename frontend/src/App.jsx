import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import Cropper from 'react-easy-crop'
import getCroppedImg from './cropImage'
import { 
  Upload, Activity, AlertTriangle, CheckCircle2, 
  ChevronRight, Stethoscope, ShieldAlert, Pill, 
  FileText, RefreshCw, Download, MapPin, Eye, ScanEye, Volume2, Layers, HelpCircle, ClipboardList
} from 'lucide-react'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

function App() {
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

  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null)
  const [isCropping, setIsCropping] = useState(false)

  useEffect(() => { return () => window.speechSynthesis.cancel() }, [])

  const onCropComplete = useCallback((croppedArea, croppedAreaPixels) => {
    setCroppedAreaPixels(croppedAreaPixels)
  }, [])

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setIsCropping(true)
      setResult(null)
    }
  }

  const handleCropConfirm = async () => {
    try {
      const croppedImage = await getCroppedImg(preview, croppedAreaPixels)
      setPreview(URL.createObjectURL(croppedImage))
      setFile(croppedImage)
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
      const response = await axios.post(`${apiUrl}/predict`, formData)
      if (response.data.error) throw new Error(response.data.error);
      setResult(response.data)
      setHeatmap(response.data.heatmap)
      setActiveTab('treatment')
    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const resetApp = () => {
    setFile(null); setPreview(null); setResult(null); setHeatmap(null);
    setPain('None'); setVision('No'); setItch('No');
    setHalos('No'); setDischarge('None'); setLightSens('No'); setSpots('No');
    window.speechSynthesis.cancel(); setIsSpeaking(false);
  }

  const speakReport = () => {
    if (!result) return
    if (isSpeaking) { window.speechSynthesis.cancel(); setIsSpeaking(false); return; }
    const text = `Diagnosis: ${result.diagnosis.replace(/_/g, ' ')}. ${result.details.advice}`
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.onend = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
    setIsSpeaking(true)
  }

  const downloadPDF = () => {
    if (!result) return;
    const doc = new jsPDF();
    const brandColor = [0, 77, 153]; 
    const accentColor = [240, 248, 255];
    
    const addHeader = (pageTitle) => {
        doc.setFillColor(...brandColor);
        doc.rect(0, 0, 210, 30, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(18);
        doc.setFont("helvetica", "bold");
        doc.text("OphthalmoAI Diagnostics", 15, 20);
        doc.setFontSize(10);
        doc.setFont("helvetica", "normal");
        doc.text(pageTitle, 200, 20, { align: 'right' });
        doc.text(`Date: ${new Date().toLocaleDateString()}`, 200, 25, { align: 'right' });
    };

    const addFooter = (pageNumber) => {
        doc.setTextColor(150, 150, 150);
        doc.setFontSize(8);
        doc.text("Disclaimer: AI screening tool only. Consult a specialist for confirmation.", 105, 285, { align: "center" });
        doc.text(`Page ${pageNumber}`, 200, 285, { align: "right" });
    };

    addHeader("Patient Report");
    
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("1. Patient Intake Form (Self-Reported)", 15, 45);
    
    autoTable(doc, {
        startY: 50,
        head: [['Symptom Category', 'Patient Response']],
        body: [
            ['Pain Level', pain],
            ['Vision Blurry?', vision],
            ['Itchiness', itch],
            ['Halos / Glare', halos],
            ['Discharge', discharge],
            ['Light Sensitivity', lightSens],
            ['Floaters / Spots', spots]
        ],
        theme: 'grid',
        headStyles: { fillColor: [100, 100, 100] },
        styles: { fontSize: 10 }
    });

    const diagnosisY = doc.lastAutoTable.finalY + 15;
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("2. AI Diagnostic Result", 15, diagnosisY);

    doc.setDrawColor(0);
    doc.setFillColor(...accentColor);
    doc.roundedRect(15, diagnosisY + 5, 180, 35, 3, 3, 'F');
    
    doc.setFontSize(16);
    doc.setTextColor(...brandColor);
    doc.text(result.diagnosis.toUpperCase().replace(/_/g, ' '), 25, diagnosisY + 20);
    
    doc.setFontSize(10);
    doc.setTextColor(50, 50, 50);
    doc.text(`Confidence Score: ${result.confidence.toFixed(1)}%`, 25, diagnosisY + 30);
    doc.text(`Severity Level: ${result.details.severity}`, 25, diagnosisY + 35); 

    const imagingY = diagnosisY + 50;
    doc.setFontSize(12);
    doc.setTextColor(0,0,0);
    doc.setFont("helvetica", "bold");
    doc.text("3. Diagnostic Imaging", 15, imagingY);

    try {
        if (preview) {
            doc.addImage(preview, 'JPEG', 15, imagingY + 5, 80, 80);
            doc.setFontSize(9);
            doc.text("Patient Scan", 55, imagingY + 90, {align: 'center'});
        }
        if (heatmap) {
            doc.addImage(heatmap, 'JPEG', 110, imagingY + 5, 80, 80);
            doc.text("AI Attention Heatmap (Grad-CAM)", 150, imagingY + 90, {align: 'center'});
        }
    } catch (e) { console.log("Image add error", e); }

    addFooter(1);

    doc.addPage();
    addHeader("Clinical Analysis");

    doc.setFontSize(12);
    doc.setTextColor(0, 0, 0);
    doc.setFont("helvetica", "bold");
    doc.text("4. Condition Details", 15, 45);

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    const descLines = doc.splitTextToSize(result.details.description, 180);
    doc.text(descLines, 15, 55);

    doc.setDrawColor(0, 77, 153);
    doc.setLineWidth(0.5);
    doc.line(15, 70, 195, 70);
    
    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 77, 153);
    doc.text("Doctor's Note / Clinical Advice:", 15, 80);
    doc.setFontSize(10);
    doc.setTextColor(0,0,0);
    doc.setFont("helvetica", "normal");
    const adviceLines = doc.splitTextToSize(result.details.advice, 180);
    doc.text(adviceLines, 15, 90);

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("5. Treatment Protocol", 15, 115);

    autoTable(doc, {
        startY: 120,
        head: [['Recommended Treatments']],
        body: result.details.treatment.map(t => [`• ${t}`]),
        theme: 'striped',
        headStyles: { fillColor: brandColor },
    });

    doc.text("6. Key Symptoms to Monitor", 15, doc.lastAutoTable.finalY + 15);
    autoTable(doc, {
        startY: doc.lastAutoTable.finalY + 20,
        head: [['Symptoms']],
        body: result.details.symptoms.map(s => [`• ${s}`]),
        theme: 'striped',
        headStyles: { fillColor: [100, 100, 100] },
    });

    addFooter(2);

    doc.addPage();
    addHeader("Action Plan");

    let yPos = 45;

    if (result.hybrid_warnings && result.hybrid_warnings.length > 0) {
        doc.setFillColor(255, 235, 238);
        doc.rect(15, yPos, 180, 25 + (result.hybrid_warnings.length * 5), 'F');
        doc.setTextColor(200, 0, 0);
        doc.setFontSize(14);
        doc.setFont("helvetica", "bold");
        doc.text("⚠️ SAFETY ALERT", 25, yPos + 10);
        
        doc.setFontSize(10);
        doc.setTextColor(0, 0, 0);
        result.hybrid_warnings.forEach((warn, i) => {
            doc.text(`• ${warn}`, 25, yPos + 20 + (i*6));
        });
        yPos += 40 + (result.hybrid_warnings.length * 5);
    }

    doc.setTextColor(0, 77, 153);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("7. Find Specialized Care", 15, yPos);

    yPos += 10;
    doc.setFillColor(245, 245, 245);
    doc.roundedRect(15, yPos, 180, 50, 3, 3, 'F');
    
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(11);
    doc.text("Based on this analysis, professional consultation is recommended.", 25, yPos + 15);
    doc.text("Click the link below to find Ophthalmologists near your current location.", 25, yPos + 25);

    doc.setTextColor(0, 0, 255);
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    const mapUrl = "https://www.google.com/maps/search/ophthalmologist+near+me";
    doc.textWithLink("CLICK HERE TO OPEN GOOGLE MAPS", 25, yPos + 40, { url: mapUrl });

    addFooter(3);

    doc.save(`Eye_Report_${new Date().toISOString().slice(0,10)}.pdf`);
  }

  const ProbabilityBar = ({ label, percentage }) => {
    const color = percentage > 80 ? 'bg-blue-600' : (percentage > 50 ? 'bg-blue-400' : 'bg-blue-300');
    return (
      <div className="space-y-1 text-sm">
        <div className="flex justify-between font-medium text-slate-700">
          <span>{label}</span>
          <span>{percentage.toFixed(1)}%</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-100">
          <div className={`${color} h-2 rounded-full transition-all duration-700`} style={{ width: `${percentage}%` }}></div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-['Inter']">
      {isCropping && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center p-4 bg-black bg-opacity-90">
            <div className="relative w-full max-w-xl h-[60vh] bg-gray-900 rounded-lg overflow-hidden">
                <Cropper image={preview} crop={crop} zoom={zoom} aspect={1} onCropChange={setCrop} onZoomChange={setZoom} onCropComplete={onCropComplete} />
            </div>
            <button onClick={handleCropConfirm} className="px-6 py-2 mt-4 text-white bg-blue-600 rounded-lg">Confirm Crop</button>
        </div>
      )}

      <nav className="sticky top-0 z-40 flex items-center h-16 px-8 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2 text-xl font-bold text-blue-900">
            <Activity className="w-6 h-6 text-blue-600" /> OphthalmoAI <span className="px-2 py-1 text-xs text-blue-600 bg-blue-100 rounded-full">Pro V4</span>
        </div>
      </nav>

      <main className="grid grid-cols-1 gap-8 px-4 py-12 mx-auto max-w-7xl lg:grid-cols-12">
        {/* LEFT: Upload & Symptoms */}
        <div className="space-y-6 lg:col-span-5">
            <div className="p-6 bg-white shadow-sm rounded-3xl">
                {!preview ? (
                    <label className="flex flex-col items-center justify-center h-64 transition border-2 border-dashed cursor-pointer border-slate-300 rounded-2xl hover:bg-blue-50">
                        <Upload className="w-10 h-10 mb-3 text-blue-400" />
                        <span className="font-medium text-slate-600">Upload Eye Scan</span>
                        <input type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                    </label>
                ) : (
                    <div className="relative h-64 overflow-hidden bg-black rounded-2xl">
                        <img src={showHeatmap && heatmap ? heatmap : preview} className="object-contain w-full h-full" />
                        {heatmap && <button onClick={() => setShowHeatmap(!showHeatmap)} className="absolute px-3 py-1 text-sm text-white rounded-full bottom-4 right-4 bg-black/70">Toggle AI Vision</button>}
                    </div>
                )}

                {/* UPDATED SYMPTOM QUESTIONNAIRE (FIXED VISIBILITY) */}
                {preview && !result && (
                    <div className="p-4 mt-6 space-y-4 border border-blue-100 bg-blue-50 rounded-xl animate-fade-in">
                        <h3 className="flex items-center gap-2 font-bold text-blue-900"><HelpCircle className="w-4 h-4"/> Patient Check</h3>
                        
                        <div className="grid grid-cols-2 gap-4">
                            {/* Basic */}
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Pain Level</label>
                                <select value={pain} onChange={(e) => setPain(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>None</option><option>Mild</option><option>Severe</option><option>Not Sure</option>
                                </select>
                            </div>
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Vision Blurry?</label>
                                <select value={vision} onChange={(e) => setVision(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>No</option><option>Yes</option><option>Not Sure</option>
                                </select>
                            </div>

                            {/* Advanced (Fixed visibility) */}
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Itchy?</label>
                                <select value={itch} onChange={(e) => setItch(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>No</option><option>Yes</option><option>Not Sure</option>
                                </select>
                            </div>
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Discharge?</label>
                                <select value={discharge} onChange={(e) => setDischarge(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>None</option><option>Watery</option><option>Thick/Yellow</option><option>Not Sure</option>
                                </select>
                            </div>
                            
                            {/* NEW FIELDS ADDED */}
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Halos / Glare?</label>
                                <select value={halos} onChange={(e) => setHalos(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>No</option><option>Yes</option><option>Not Sure</option>
                                </select>
                            </div>
                            <div>
                                <label className="block mb-1 text-xs font-bold text-slate-500">Light Sensitive?</label>
                                <select value={lightSens} onChange={(e) => setLightSens(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>No</option><option>Yes</option><option>Not Sure</option>
                                </select>
                            </div>
                            <div className="col-span-2">
                                <label className="block mb-1 text-xs font-bold text-slate-500">Seeing Spots/Floaters?</label>
                                <select value={spots} onChange={(e) => setSpots(e.target.value)} className="w-full p-2 text-sm border rounded">
                                    <option>No</option><option>Yes</option><option>Not Sure</option>
                                </select>
                            </div>
                        </div>
                    </div>
                )}

                <button onClick={handleAnalyze} disabled={!file || loading} className="w-full py-4 mt-4 font-bold text-white transition-all bg-blue-600 shadow-lg rounded-xl hover:bg-blue-700">
                    {loading ? 'Analyzing...' : 'Run Diagnosis'}
                </button>
                {result && <button onClick={resetApp} className="w-full py-2 mt-2 rounded-lg text-slate-500 hover:bg-slate-100">Reset</button>}
            </div>
        </div>

        {/* RIGHT: Results */}
        <div className="lg:col-span-7">
            {result ? (
                <div className="space-y-6 animate-fade-in">
                    <div className={`p-6 rounded-3xl shadow-xl text-white flex justify-between items-center ${result.diagnosis === 'Normal' ? 'bg-emerald-500' : 'bg-rose-600'}`}>
                        <div>
                            <p className="text-sm font-medium uppercase opacity-90">AI Diagnosis</p>
                            <h2 className="text-3xl font-bold">{result.diagnosis.replace(/_/g, ' ')}</h2>
                            <p className="mt-1 opacity-90">{result.confidence.toFixed(1)}% Confidence</p>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={speakReport} className={`p-2 rounded-full hover:bg-white/30 ${isSpeaking ? 'bg-white text-rose-600' : 'bg-white/20'}`}><Volume2/></button>
                            <button onClick={downloadPDF} className="p-2 rounded-full bg-white/20 hover:bg-white/30"><Download/></button>
                        </div>
                    </div>

                    {/* HYBRID WARNINGS */}
                    {result.hybrid_warnings && result.hybrid_warnings.length > 0 && (
                        <div className="p-4 border-l-4 shadow-sm bg-amber-50 border-amber-500 rounded-xl">
                            <h4 className="flex items-center gap-2 font-bold text-amber-800"><ShieldAlert className="w-5 h-5"/> Safety Alerts</h4>
                            {result.hybrid_warnings.map((w, i) => <p key={i} className="mt-1 text-sm text-amber-700">{w}</p>)}
                        </div>
                    )}

                    {/* MEDICAL TABS */}
                    <div className="p-6 bg-white border shadow-lg rounded-3xl border-slate-200">
                        <div className="flex gap-4 pb-4 mb-4 overflow-x-auto border-b border-slate-100">
                            <button onClick={() => setActiveTab('treatment')} className={`font-bold pb-2 border-b-2 transition-colors ${activeTab === 'treatment' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}>Treatment Plan</button>
                            <button onClick={() => setActiveTab('doctor')} className={`font-bold pb-2 border-b-2 transition-colors ${activeTab === 'doctor' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}>Doctor's Note</button>
                            <button onClick={() => setActiveTab('symptoms')} className={`font-bold pb-2 border-b-2 transition-colors ${activeTab === 'symptoms' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}>Symptoms</button>
                            <button onClick={() => setActiveTab('stats')} className={`font-bold pb-2 border-b-2 transition-colors ${activeTab === 'stats' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400'}`}>Stats</button>
                        </div>

                        <div className="min-h-[200px]">
                            {/* 1. TREATMENT TAB */}
                            {activeTab === 'treatment' && (
                                <div className="space-y-4 animate-fade-in">
                                    <h4 className="text-sm font-bold tracking-wider uppercase text-slate-400">Recommended Plan</h4>
                                    <div className="space-y-3">
                                        {result.details.treatment.map((t, i) => (
                                            <div key={i} className="flex items-start gap-3 p-3 text-green-900 border border-green-100 rounded-lg bg-green-50">
                                                <Pill className="w-5 h-5 mt-0.5 text-green-600" />
                                                {t}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* 2. DOCTOR'S NOTE TAB */}
                            {activeTab === 'doctor' && (
                                <div className="space-y-4 animate-fade-in">
                                    <div className="p-4 border border-blue-100 bg-blue-50 rounded-xl">
                                        <h4 className="flex items-center gap-2 mb-2 font-bold text-blue-900">
                                            <Stethoscope className="w-4 h-4" /> Clinical Assessment
                                        </h4>
                                        <p className="leading-relaxed text-slate-700">{result.details.advice}</p>
                                    </div>
                                    <div className="p-4 border rounded-xl bg-slate-50 border-slate-100">
                                         <p className="text-sm text-slate-500"><strong>Severity Level:</strong> {result.details.severity}</p>
                                         <p className="mt-1 text-sm text-slate-500"><strong>Condition Description:</strong> {result.details.description}</p>
                                    </div>
                                    <a href="https://www.google.com/maps/search/ophthalmologist+near+me" target="_blank" className="block w-full py-3 font-bold text-center text-blue-600 transition border-2 border-blue-100 rounded-xl hover:bg-blue-50">
                                        Find Nearby Specialist ↗
                                    </a>
                                </div>
                            )}

                            {/* 3. SYMPTOMS TAB */}
                            {activeTab === 'symptoms' && (
                                <div className="space-y-4 animate-fade-in">
                                     <h4 className="text-sm font-bold tracking-wider uppercase text-slate-400">Typical Symptoms</h4>
                                     <ul className="grid grid-cols-1 gap-2">
                                        {result.details.symptoms.map((s, i) => (
                                            <li key={i} className="flex items-center gap-3 p-2 text-slate-700">
                                                <div className="w-2 h-2 rounded-full bg-amber-400" />
                                                {s}
                                            </li>
                                        ))}
                                     </ul>
                                </div>
                            )}

                            {/* 4. STATS TAB */}
                            {activeTab === 'stats' && (
                                <div className="space-y-4 animate-fade-in">
                                    <p className="text-sm text-slate-500">AI Confidence breakdown by class:</p>
                                    <div className="space-y-3">
                                        {Object.entries(result.probabilities)
                                            .sort(([, a], [, b]) => b - a)
                                            .map(([label, percentage], i) => (
                                            <ProbabilityBar key={i} label={label.replace(/_/g, ' ')} percentage={percentage} />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ) : (
                <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-3xl bg-slate-50/50">
                    <Activity className="w-16 h-16 mb-4 opacity-20" />
                    <p>Ready to Analyze</p>
                </div>
            )}
        </div>
      </main>
    </div>
  )
}

export default App