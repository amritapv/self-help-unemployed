import { useEffect, useRef, useState } from 'react'
import { TEST_PERSONAS, matchTestCommand } from './testPersonas'
import { t } from './i18n'

const API_URL = 'http://localhost:8000'

// Tiny helper for the {placeholder} templates in the i18n strings.
function fmt(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`))
}

function ChatView({ country, language, onProfileComplete }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: t(language, 'greeting') }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [collectedData, setCollectedData] = useState(null)

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
    prevLangRef.current = language
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language])

  // Shared assessment chain: /assess-skills -> /match-opportunities -> render top 5.
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

      // 3. Format top 5 as a chat message
      const summary = profile.portable_summary || ''
      const n = opportunities.length
      const intro = summary
        ? fmt(t(language, 'basedOnInput'), { summary, n })
        : fmt(t(language, 'topNOpportunities'), { n })

      const oppLines = opportunities.slice(0, 5).map((opp, i) => {
        const lines = [
          `\n${i + 1}. ${opp.title}`,
          `   ${t(language, 'whyItFits')}: ${opp.fit_explanation}`,
          `   ${t(language, 'wage')}: ${opp.wage_range}`,
          `   ${t(language, 'outlook')}: ${opp.sector_growth || opp.sector_growth_signal}`,
        ]
        if (opp.skill_gap) lines.push(`   ${t(language, 'gap')}: ${opp.skill_gap}`)
        lines.push(`   ${t(language, 'nextStep')}: ${opp.next_step}`)
        return lines.join('\n')
      }).join('\n')

      const finalMessage = oppLines
        ? `${intro}\n${oppLines}`
        : (oppsData.note ? `${oppsData.note}` : t(language, 'noMatchFallback'))

      setMessages(prev => [...prev, { role: 'assistant', content: finalMessage }])
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

    // Hotkey: "Test: Amara" / "Test: Bern" / "Test: Cal" — skip the chat, run the chain directly.
    const persona = matchTestCommand(input)
    if (persona) {
      const userMessage = { role: 'user', content: input.trim() }
      setMessages(prev => [
        ...prev,
        userMessage,
        { role: 'assistant', content: fmt(t(language, 'loadingPersona'), { label: persona.label }) },
      ])
      setInput('')
      const { country_code, ...collected } = persona.payload
      await runAssessment({ collected, country_code })
      return
    }

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
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`p-3 rounded-lg max-w-[85%] whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white ms-auto'
                : 'bg-gray-200 text-gray-800'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="bg-gray-200 text-gray-800 p-3 rounded-lg max-w-[85%]">
            <span className="animate-pulse">...</span>
          </div>
        )}
      </div>

      {collectedData && (
        <div className="mx-4 mb-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800 mb-2">{t(language, 'readyToAnalyze')}</p>
          <button
            onClick={handleAssess}
            disabled={loading}
            className="w-full bg-green-600 text-white p-2 rounded font-semibold disabled:opacity-50"
          >
            {t(language, 'generateProfileButton')}
          </button>
        </div>
      )}

      <div className="flex gap-2 p-4 border-t">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={t(language, 'inputPlaceholder')}
          disabled={loading}
          className="flex-1 border rounded-lg p-3 disabled:bg-gray-100"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-6 rounded-lg disabled:opacity-50"
        >
          {t(language, 'sendButton')}
        </button>
      </div>
    </div>
  )
}

export default ChatView
