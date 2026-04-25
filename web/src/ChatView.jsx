import { useState, useRef, useEffect } from 'react'

const API_URL = 'http://localhost:8000'

// Web Speech API support check
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

function ChatView({ country, onProfileComplete }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! I'm here to help you understand your skills and find opportunities. Let's start - what's your educational background? This could be formal schooling, certifications, or any training you've done." }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [collectedData, setCollectedData] = useState(null)
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
          country_code: country
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
        content: "Sorry, I'm having trouble connecting. Please try again."
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleAssess = async () => {
    if (!collectedData) return

    setLoading(true)
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: 'Analyzing your skills profile...'
    }])

    try {
      const response = await fetch(`${API_URL}/assess-skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...collectedData,
          country_code: country
        })
      })

      const profile = await response.json()
      onProfileComplete(profile)
    } catch (error) {
      console.error('Assessment error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, I couldn't complete the assessment. Please try again."
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[75vh]">
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg max-w-[85%] ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white ml-auto'
                : 'bg-gray-200 text-gray-800'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="bg-gray-200 text-gray-800 p-3 rounded-lg max-w-[85%]">
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}
      </div>

      {collectedData && (
        <div className="mx-4 mb-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800 mb-2">Ready to analyze your skills!</p>
          <button
            onClick={handleAssess}
            disabled={loading}
            className="w-full bg-green-600 text-white p-2 rounded font-semibold disabled:opacity-50"
          >
            Generate My Skills Profile
          </button>
        </div>
      )}

      <div className="flex gap-2 p-4 border-t">
        {SpeechRecognition && (
          <select
            value={speechLang}
            onChange={(e) => { setSpeechLang(e.target.value); if (isListening) recognitionRef.current?.stop() }}
            className="border rounded-lg px-2 text-sm text-gray-600 bg-white"
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
          placeholder={isListening ? 'Listening...' : 'Type or speak your message...'}
          disabled={loading}
          className={`flex-1 border rounded-lg p-3 disabled:bg-gray-100 ${isListening ? 'border-red-400 bg-red-50' : ''}`}
        />
        {SpeechRecognition && (
          <button
            onClick={toggleListening}
            disabled={loading}
            title={isListening ? 'Stop listening' : 'Speak your answer'}
            className={`px-4 rounded-lg transition-colors disabled:opacity-50 ${
              isListening
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
          >
            🎤
          </button>
        )}
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-6 rounded-lg disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatView
