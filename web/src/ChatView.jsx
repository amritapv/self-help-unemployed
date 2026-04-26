import { useEffect, useRef, useState } from 'react'
import { t } from './i18n'

const API_URL = 'http://localhost:8000'

// Web Speech API support check
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

// Tiny helper for the {placeholder} templates in the i18n strings.
function fmt(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`))
}

function ChatView({ country, language, onProfileComplete, onNavigate }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: t(language, 'greeting') }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [collectedData, setCollectedData] = useState(null)
  const [assessmentReady, setAssessmentReady] = useState(false)
  const [hasOpportunities, setHasOpportunities] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speechLang, setSpeechLang] = useState('en-US')
  const recognitionRef = useRef(null)

  const SPEECH_LANGUAGES = [
    { label: 'English', code: 'en-US' },
    { label: 'Hindi', code: 'hi-IN' },
    { label: 'Telugu', code: 'te-IN' },
    { label: 'Japanese', code: 'ja-JP' },
    { label: 'Tagalog', code: 'fil-PH' },
    { label: 'Spanish', code: 'es-ES' },
  ]

  useEffect(() => {
    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = speechLang

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(r => r[0].transcript)
        .join('')
      setInput(transcript)
    }

    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)

    recognitionRef.current = recognition
  }, [speechLang])

  const toggleListening = () => {
    if (!recognitionRef.current) return
    if (isListening) {
      recognitionRef.current.stop()
    } else {
      setInput('')
      recognitionRef.current.start()
      setIsListening(true)
    }
  }

  // Reset chat when language changes. First switch (still on default greeting only)
  // happens silently. Once the user has interacted, we confirm before resetting.
  const prevLangRef = useRef(language)
  useEffect(() => {
    if (prevLangRef.current === language) return
    const hasInteraction = messages.length > 1
    if (hasInteraction) {
      const ok = window.confirm(t(language, 'confirmLanguageSwitch'))
      if (!ok) {
        // User declined — nothing to do, but we still update the ref so we don't
        // re-prompt on every render.
        prevLangRef.current = language
        return
      }
    }
    setMessages([{ role: 'assistant', content: t(language, 'greeting') }])
    setCollectedData(null)
    setAssessmentReady(false)
    setHasOpportunities(false)
    prevLangRef.current = language
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  // Shared assessment chain: /assess-skills -> /match-opportunities -> render top 3.
  const runAssessment = async ({ collected, country_code }) => {
    setLoading(true)
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: t(language, 'analyzingMessage') }
    ])

    try {
      // 1. Skills assessment (Module 01)
      const profileRes = await fetch(`${API_URL}/assess-skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...collected, country_code, language })
      })
      const profile = await profileRes.json()

      // 2. Opportunity matching (Module 03)
      const oppsRes = await fetch(`${API_URL}/match-opportunities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills_profile: profile, country_code, language })
      })
      const oppsData = await oppsRes.json()
      const opportunities = oppsData.opportunities || []

      // 3. Format a CONCISE chat message. Detail lives on the Skills Profile
      // and Job Opportunities tabs — the chat just gives a one-glance summary
      // and points users to the dedicated screens.
      const summary = profile.portable_summary || ''
      const n = opportunities.length
      const risk = profile.automation_risk
      const sections = []

      if (summary) sections.push(summary)

      if (risk && risk.verdict && risk.verdict !== 'unknown') {
        sections.push(`${t(language, 'automationOutlook')}: ${risk.verdict_label}.`)
      }

      if (n > 0) {
        sections.push(
          `${fmt(t(language, 'topNOpportunities'), { n })}\n\n` +
          `Tap the **Skills Profile** and **Job Opportunities** tabs above for the full breakdown.`
        )
      }

      const finalMessage = sections.length
        ? sections.join('\n\n')
        : (oppsData.note ? `${oppsData.note}` : t(language, 'noMatchFallback'))

      setMessages(prev => [...prev, { role: 'assistant', content: finalMessage }])
      setAssessmentReady(!!profile)
      setHasOpportunities(opportunities.length > 0)
      onProfileComplete?.({ profile, opportunities, country: country_code })
    } catch (error) {
      console.error('Assessment error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: t(language, 'assessmentError')
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages,
          country_code: country,
          language
        })
      })

      const data = await response.json()

      setMessages([...newMessages, { role: 'assistant', content: data.message }])

      if (data.ready_for_assessment && data.collected_data) {
        setCollectedData(data.collected_data)
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages([...newMessages, {
        role: 'assistant',
        content: t(language, 'connectionError')
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleAssess = async () => {
    if (!collectedData) return
    await runAssessment({ collected: collectedData, country_code: country })
  }

  return (
    <div className="flex flex-col h-[75vh]">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-[11px] font-bold shadow-sm">
                Shu
              </div>
            )}
            <div
              className={`px-4 py-3 rounded-2xl max-w-[80%] whitespace-pre-wrap text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white shadow-md rounded-tr-sm'
                  : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-tl-sm'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
              U
            </div>
            <div className="bg-white shadow-sm border border-gray-100 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5">
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        {/* Action buttons after the assessment lands — quick-jump to the dedicated screens. */}
        {assessmentReady && !loading && onNavigate && (
          <div className="flex flex-wrap gap-2 ms-10">
            <button
              onClick={() => onNavigate('skills')}
              className="bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium shadow-sm hover:shadow-md hover:bg-blue-700 transition"
            >
              See Skills Profile →
            </button>
            {hasOpportunities && (
              <button
                onClick={() => onNavigate('opps')}
                className="bg-gradient-to-r from-emerald-500 to-green-600 text-white px-4 py-2 rounded-full text-sm font-medium shadow-sm hover:shadow-md hover:brightness-110 transition"
              >
                See Job Opportunities →
              </button>
            )}
          </div>
        )}
      </div>

      {collectedData && (
        <div className="mx-4 mb-3 p-4 bg-gradient-to-br from-emerald-50 to-green-50 border border-emerald-200 rounded-2xl shadow-sm">
          <p className="text-sm text-emerald-800 mb-2 font-medium">{t(language, 'readyToAnalyze')}</p>
          <button
            onClick={handleAssess}
            disabled={loading}
            className="w-full bg-gradient-to-r from-emerald-500 to-green-600 text-white p-2.5 rounded-xl font-semibold shadow-sm hover:shadow-md hover:brightness-110 transition disabled:opacity-50"
          >
            {t(language, 'generateProfileButton')}
          </button>
        </div>
      )}

      <div className={`m-4 bg-white rounded-2xl shadow-md border transition-all ${
        isListening ? 'border-red-300 ring-2 ring-red-100' : 'border-gray-100 focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300'
      }`}>
        <div className="flex items-center gap-2 p-2">
          {SpeechRecognition && (
            <select
              value={speechLang}
              onChange={(e) => { setSpeechLang(e.target.value); if (isListening) recognitionRef.current?.stop() }}
              className="text-xs text-gray-600 bg-gray-50 border-0 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-200"
            >
              {SPEECH_LANGUAGES.map(l => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          )}
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isListening ? 'Listening...' : t(language, 'inputPlaceholder')}
            disabled={loading}
            className="flex-1 border-0 px-2 py-2 text-sm bg-transparent focus:outline-none disabled:opacity-50"
          />
          {SpeechRecognition && (
            <button
              onClick={toggleListening}
              disabled={loading}
              title={isListening ? 'Stop listening' : 'Speak your answer'}
              className={`w-9 h-9 flex items-center justify-center rounded-full transition disabled:opacity-50 ${
                isListening
                  ? 'bg-red-500 text-white animate-pulse shadow-md'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              🎤
            </button>
          )}
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white px-5 py-2 rounded-full text-sm font-medium shadow-sm hover:shadow-md hover:bg-blue-700 transition disabled:opacity-50 disabled:hover:shadow-sm disabled:hover:bg-blue-600"
          >
            {t(language, 'sendButton')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatView
