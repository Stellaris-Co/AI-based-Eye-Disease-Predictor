import { useState } from 'react'
import axios from 'axios'
import { 
  Upload, Activity, AlertTriangle, CheckCircle2, 
  ChevronRight, Stethoscope, ShieldAlert, Pill, 
  FileText, RefreshCw
} from 'lucide-react'

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setResult(null)
    }
  }

  const handleAnalyze = async () => {
    if (!file) return
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8000/predict', formData)
      setResult(response.data)
    } catch (error) {
      console.error("Error:", error)
      alert("Could not connect to the AI Brain. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  const resetApp = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-blue-100">
      
      {/* NAVBAR */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50 backdrop-blur-md bg-white/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-blue-500">
              OphthalmoAI
            </span>
          </div>
          <div className="text-xs font-medium text-slate-400 border border-slate-200 px-3 py-1 rounded-full">
            v2.0 Pro • EfficientNetB3
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* LEFT COLUMN - UPLOAD */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-1">
              <div className="p-6 border-b border-slate-100">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Upload className="w-5 h-5 text-blue-600" />
                  Input Scan
                </h2>
              </div>
              
              <div className="p-6">
                {!preview ? (
                  <label className="flex flex-col items-center justify-center w-full h-80 border-2 border-dashed border-slate-300 rounded-2xl cursor-pointer bg-slate-50 hover:bg-blue-50 hover:border-blue-400 transition-all group">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <div className="bg-white p-4 rounded-full shadow-sm mb-4 group-hover:scale-110 transition-transform">
                        <Upload className="w-8 h-8 text-blue-500" />
                      </div>
                      <p className="mb-2 text-sm text-slate-600 font-medium">Click to upload analysis image</p>
                      <p className="text-xs text-slate-400">JPG, PNG supported</p>
                    </div>
                    <input type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                  </label>
                ) : (
                  <div className="relative group rounded-2xl overflow-hidden shadow-md">
                    <img src={preview} alt="Scan" className="w-full h-80 object-cover" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <button onClick={resetApp} className="bg-white text-slate-900 px-4 py-2 rounded-full font-medium text-sm flex items-center gap-2 hover:bg-slate-100">
                        <RefreshCw className="w-4 h-4" /> Change Image
                      </button>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleAnalyze}
                  disabled={!file || loading}
                  className={`w-full mt-6 py-4 px-6 rounded-xl font-bold text-white shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 transition-all
                    ${loading 
                      ? 'bg-slate-400 cursor-not-allowed shadow-none' 
                      : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:translate-y-[-2px] hover:shadow-blue-500/40 active:translate-y-[0px]'
                    }`}
                >
                  {loading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Run Diagnostics <ChevronRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN - RESULTS */}
          <div className="lg:col-span-7">
            {result ? (
              <div className="animate-fade-in space-y-6">
                
                {/* MAIN DIAGNOSIS CARD */}
                <div className={`rounded-3xl p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6
                  ${result.diagnosis === 'Normal' 
                    ? 'bg-gradient-to-br from-emerald-500 to-teal-600 shadow-emerald-500/20' 
                    : 'bg-gradient-to-br from-rose-500 to-red-600 shadow-rose-500/20'}`}>
                  
                  <div>
                    <div className="flex items-center gap-2 opacity-90 mb-1 text-sm font-medium tracking-wide uppercase">
                      Analysis Complete
                    </div>
                    <h2 className="text-4xl font-bold mb-2">{result.diagnosis}</h2>
                    <p className="opacity-90 flex items-center gap-2">
                      <span className="bg-white/20 px-2 py-1 rounded-md text-sm backdrop-blur-sm">
                        {result.confidence.toFixed(1)}% Confidence
                      </span>
                    </p>
                  </div>
                  
                  <div className="bg-white/20 p-4 rounded-2xl backdrop-blur-md">
                    {result.diagnosis === 'Normal' ? <CheckCircle2 className="w-12 h-12" /> : <AlertTriangle className="w-12 h-12" />}
                  </div>
                </div>

                {/* DETAILS TABS */}
                <div className="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
                  <div className="flex border-b border-slate-100">
                    <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} icon={<FileText className="w-4 h-4" />} label="Overview" />
                    <TabButton active={activeTab === 'treatment'} onClick={() => setActiveTab('treatment')} icon={<Pill className="w-4 h-4" />} label="Treatment" />
                    <TabButton active={activeTab === 'doctor'} onClick={() => setActiveTab('doctor')} icon={<Stethoscope className="w-4 h-4" />} label="Doctor's Note" />
                  </div>

                  <div className="p-8 min-h-[300px]">
                    {activeTab === 'overview' && (
                      <div className="animate-fade-in space-y-4">
                        <h3 className="text-xl font-bold text-slate-800">Condition Details</h3>
                        <p className="text-slate-600 leading-relaxed">{result.details.description}</p>
                        
                        <div className="mt-6">
                          <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Common Symptoms</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {result.details.symptoms.map((sym, i) => (
                              <div key={i} className="flex items-start gap-2 text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 shrink-0" />
                                {sym}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {activeTab === 'treatment' && (
                      <div className="animate-fade-in space-y-6">
                        <div>
                          <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Recommended Actions</h4>
                          <div className="space-y-3">
                            {result.details.treatment.map((t, i) => (
                              <div key={i} className="flex items-center gap-3 p-4 bg-blue-50/50 border border-blue-100 rounded-xl text-blue-800">
                                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                                {t}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {activeTab === 'doctor' && (
                      <div className="animate-fade-in">
                        <div className={`p-6 rounded-xl border-l-4 ${result.diagnosis === 'Normal' ? 'bg-emerald-50 border-emerald-500' : 'bg-amber-50 border-amber-500'}`}>
                          <h4 className="font-bold flex items-center gap-2 mb-2">
                            <ShieldAlert className="w-5 h-5" /> Clinical Recommendation
                          </h4>
                          <p className="text-slate-700">{result.details.severity === 'None' ? "Routine Checkup Recommended" : "Professional Consultation Required"}</p>
                        </div>
                        
                        <div className="mt-6 space-y-4">
                          <p className="text-slate-600">
                            <strong>Assessment:</strong> The AI has detected patterns consistent with {result.diagnosis}. 
                            {result.diagnosis !== 'Normal' && " This requires clinical correlation."}
                          </p>
                          
                          <div className="bg-slate-900 text-slate-300 p-4 rounded-lg text-sm font-mono">
                            SEVERITY_LEVEL: {result.details.severity.toUpperCase()}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

              </div>
            ) : (
              <div className="h-full min-h-[500px] bg-white rounded-3xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-center p-8">
                <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                  <Activity className="w-10 h-10 text-slate-300" />
                </div>
                <h3 className="text-xl font-bold text-slate-400">Awaiting Scan</h3>
                <p className="text-slate-400 max-w-xs mx-auto mt-2">Upload an eye image on the left panel to generate a comprehensive AI medical report.</p>
              </div>
            )}
          </div>
          
        </div>
      </main>
    </div>
  )
}

const TabButton = ({ active, onClick, icon, label }) => (
  <button 
    onClick={onClick}
    className={`flex-1 py-4 flex items-center justify-center gap-2 text-sm font-medium transition-all relative
      ${active ? 'text-blue-600' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}
  >
    {icon}
    {label}
    {active && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
  </button>
)

export default App