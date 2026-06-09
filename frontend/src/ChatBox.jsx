import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { MessageCircle, X, Send, Loader2, Bot, User, AlertCircle, Sparkles, ChevronDown } from 'lucide-react'

const QUICK_QUESTIONS = [
  "What are the early signs of cataracts?",
  "How can I prevent eye disease?",
  "When should I see an eye doctor urgently?",
  "What does my diagnosis mean?",
]

const TypingDots = () => (
  <div className="flex items-center gap-1 px-3 py-2.5">
    {[0, 1, 2].map(i => (
      <span
        key={i}
        className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-bounce"
        style={{ animationDelay: `${i * 0.15}s`, animationDuration: '0.8s' }}
      />
    ))}
  </div>
)

const ChatBot = ({ diagnosisContext }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: diagnosisContext
        ? `Hello! I can see you've received an AI screening result for **${diagnosisContext.diagnosis}**. I'm here to help you understand this condition, discuss your symptoms, prevention strategies, and when to seek professional care. What would you like to know?`
        : "Hello! I'm OphthalmoAI Doctor, your AI eye health assistant. I can help you understand eye conditions, symptoms, and when to seek care. How can I help you today?"
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isOpen && !isMinimized && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isOpen, isMinimized])

  useEffect(() => {
    if (isOpen && !isMinimized && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen, isMinimized])

  
  useEffect(() => {
    if (diagnosisContext && messages.length === 1) {
      setMessages([{
        role: 'assistant',
        content: `Hello! I can see your AI screening detected **${diagnosisContext.diagnosis}** with ${diagnosisContext.confidence?.toFixed(1)}% confidence. I'm here to help you understand this result, discuss symptoms, prevention, and next steps. What would you like to know?`
      }])
    }
  }, [diagnosisContext, messages.length])

  const sendMessage = async (text) => {
    const messageText = text || input.trim()
    if (!messageText || loading) return

    const userMessage = { role: 'user', content: messageText }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput('')
    setLoading(true)

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await axios.post(`${apiUrl}/chat`, {
        message: messageText,
        history: messages.slice(1), 
        diagnosis_context: diagnosisContext || null
      })

      setMessages([...updatedMessages, {
        role: 'assistant',
        content: response.data.reply
      }])
    } catch {
      setMessages([...updatedMessages, {
        role: 'assistant',
        content: "I'm having trouble connecting to the server. Please check that the backend is running and try again. For urgent eye concerns, contact a qualified ophthalmologist directly."
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatMessage = (content) => {
    return content.split('**').map((part, i) =>
      i % 2 === 1
        ? <strong key={i} className="font-semibold">{part}</strong>
        : part
    )
  }

  const NAVY = '#0d2137'
  const TEAL = '#00adb5'

  return (
    <>
      
      <button
        onClick={() => { setIsOpen(!isOpen); setIsMinimized(false) }}
        className="fixed z-50 flex items-center justify-center transition-all duration-300 rounded-full shadow-xl bottom-6 right-6 w-14 h-14 hover:scale-110 active:scale-95"
        style={{
          background: isOpen
            ? 'linear-gradient(135deg, #0f2d4a, #0d4f6e)'
            : 'linear-gradient(135deg, #00adb5, #007a80)',
          boxShadow: '0 8px 32px rgba(0, 173, 181, 0.4)'
        }}
        aria-label={isOpen ? 'Close AI Doctor chat' : 'Open AI Doctor chat'}
      >
        {isOpen
          ? <X className="w-6 h-6 text-white" />
          : <MessageCircle className="w-6 h-6 text-white" />
        }
      </button>

      
      {isOpen && (
        <div
          className="fixed z-50 flex flex-col overflow-hidden border bottom-24 right-6 rounded-2xl"
          style={{
            width: 'min(380px, calc(100vw - 48px))',
            height: isMinimized ? 'auto' : '520px',
            background: '#ffffff',
            borderColor: '#e2e8f0',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 24px rgba(0, 173, 181, 0.12)',
          }}
        >
          
          <div
            className="flex items-center gap-3 px-4 py-3 shrink-0"
            style={{ background: 'linear-gradient(135deg, #0d2137 0%, #0d4f6e 100%)' }}
          >
            <div className="flex items-center justify-center rounded-full w-9 h-9"
              style={{ background: 'rgba(0,173,181,0.25)', border: '1px solid rgba(0,173,181,0.4)' }}>
              <Bot className="w-5 h-5" style={{ color: TEAL }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold leading-tight text-white">OphthalmoAI Doctor</p>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <p className="text-xs" style={{ color: '#7ecfe0' }}>
                  {diagnosisContext ? `Context: ${diagnosisContext.diagnosis}` : 'AI Eye Health Assistant'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 transition rounded-lg hover:bg-white/10 text-white/60 hover:text-white"
              aria-label={isMinimized ? 'Expand chat' : 'Minimise chat'}
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${isMinimized ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {!isMinimized && (
            <>
              
              <div className="flex items-start gap-2 px-3 py-2 shrink-0"
                style={{ background: '#fffbeb', borderBottom: '1px solid #fde68a' }}>
                <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: '#d97706' }} />
                <p className="text-[10px] leading-tight" style={{ color: '#92400e' }}>
                  For educational guidance only. Not a substitute for professional medical diagnosis or treatment.
                </p>
              </div>

              
              <div className="flex-1 p-4 space-y-3 overflow-y-auto" style={{ background: '#f8fafc' }}>
                {messages.map((msg, i) => (
                  <div key={i} className={`flex items-end gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div
                      className="flex items-center justify-center rounded-full w-7 h-7 shrink-0"
                      style={{
                        background: msg.role === 'assistant'
                          ? 'rgba(0,173,181,0.12)'
                          : 'rgba(99, 102, 241, 0.12)'
                      }}
                    >
                      {msg.role === 'assistant'
                        ? <Bot className="w-3.5 h-3.5" style={{ color: TEAL }} />
                        : <User className="w-3.5 h-3.5" style={{ color: '#6366f1' }} />
                      }
                    </div>
                    <div
                      className="max-w-[78%] px-3 py-2 rounded-2xl text-sm leading-relaxed"
                      style={msg.role === 'assistant'
                        ? {
                          background: '#ffffff',
                          color: '#1e293b',
                          border: '1px solid #e2e8f0',
                          borderBottomLeftRadius: '4px',
                          boxShadow: '0 1px 4px rgba(0,0,0,0.06)'
                        }
                        : {
                          background: 'linear-gradient(135deg, #0d2137, #0d4f6e)',
                          color: '#ffffff',
                          borderBottomRightRadius: '4px',
                        }
                      }
                    >
                      {formatMessage(msg.content)}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex items-end gap-2">
                    <div className="flex items-center justify-center rounded-full w-7 h-7 shrink-0"
                      style={{ background: 'rgba(0,173,181,0.12)' }}>
                      <Bot className="w-3.5 h-3.5" style={{ color: TEAL }} />
                    </div>
                    <div className="border rounded-2xl"
                      style={{
                        background: '#ffffff', border: '1px solid #e2e8f0',
                        borderBottomLeftRadius: '4px', boxShadow: '0 1px 4px rgba(0,0,0,0.06)'
                      }}>
                      <TypingDots />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              
              {messages.length <= 2 && !loading && (
                <div className="px-3 pb-2 shrink-0" style={{ background: '#f8fafc' }}>
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Sparkles className="w-3 h-3" style={{ color: TEAL }} />
                    <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>
                      Quick questions
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_QUESTIONS.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(q)}
                        className="text-[10px] px-2 py-1 rounded-full border transition-all hover:scale-105 active:scale-95"
                        style={{ background: 'white', border: '1px solid #cbd5e1', color: '#475569' }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              
              <div className="p-3 shrink-0" style={{ background: '#ffffff', borderTop: '1px solid #e2e8f0' }}>
                <div className="flex gap-2">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about eye health, symptoms, treatment..."
                    rows={1}
                    className="flex-1 text-sm px-3 py-2.5 rounded-xl resize-none outline-none transition-all"
                    style={{
                      border: '1.5px solid #e2e8f0',
                      color: '#1e293b',
                      fontFamily: 'inherit',
                      maxHeight: '80px',
                    }}
                    onFocus={e => e.target.style.borderColor = TEAL}
                    onBlur={e => e.target.style.borderColor = '#e2e8f0'}
                  />
                  <button
                    onClick={() => sendMessage()}
                    disabled={loading || !input.trim()}
                    className="flex items-center justify-center w-10 h-10 transition-all rounded-xl hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 shrink-0"
                    style={{ background: 'linear-gradient(135deg, #00adb5, #007a80)' }}
                    aria-label="Send message"
                  >
                    {loading
                      ? <Loader2 className="w-4 h-4 text-white animate-spin" />
                      : <Send className="w-4 h-4 text-white" />
                    }
                  </button>
                </div>
                
                <p className="text-center text-[9px] mt-1.5" style={{ color: '#94a3b8' }}>
                  Powered by OphthalmoAI · Press Enter to send
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  )
}

export default ChatBot
