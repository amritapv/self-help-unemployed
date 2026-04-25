import { useState } from 'react'
import { TEST_PERSONAS, matchTestCommand } from './testPersonas'

const API_URL = 'http://localhost:8000'

function ChatView({ country, onProfileComplete }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        "Hi! I'm here to help you understand your skills and find opportunities. Let's start - what's your educational background? This could be formal schooling, certifications, or any training you've done.\n\n" +
        "Tip: type 'Test: Amara', 'Test: Bern', or 'Test: Cal' to skip the chat and run a simulated assessment with a pre-built persona."
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [collectedData, setCollectedData] = useState(null)

  // Shared assessment chain: /assess-skills -> /match-opportunities -> render top 5.
  const runAssessment = async ({ collected, country_code }) => {
    setLoading(true)
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: 'Analyzing your skills and finding opportunities...' }
    ])

    try {
      // 1. Skills assessment (Module 01)
      const profileRes = await fetch(`${API_URL}/assess-skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...collected, country_code })
      })
      const profile = await profileRes.json()

      // 2. Opportunity matching (Module 03)
      const oppsRes = await fetch(`${API_URL}/match-opportunities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills_profile: profile, country_code })
      })
      const oppsData = await oppsRes.json()
      const opportunities = oppsData.opportunities || []

      // 3. Format top 5 as a chat message
      const summary = profile.portable_summary || ''
      const intro = summary
        ? `Based on what you told me:\n\n${summary}\n\nHere are your top ${opportunities.length} opportunities:`
        : `Here are your top ${opportunities.length} opportunities:`

      const oppLines = opportunities.slice(0, 5).map((opp, i) => {
        const lines = [
          `\n${i + 1}. ${opp.title}`,
          `   Why it fits: ${opp.fit_explanation}`,
          `   Wage: ${opp.wage_range}`,
          `   Outlook: ${opp.sector_growth || opp.sector_growth_signal}`,
        ]
        if (opp.skill_gap) lines.push(`   Gap: ${opp.skill_gap}`)
        lines.push(`   Next step: ${opp.next_step}`)
        return lines.join('\n')
      }).join('\n')

      const finalMessage = oppLines
        ? `${intro}\n${oppLines}`
        : `I couldn't find a good match — ${oppsData.note || 'try giving me a bit more detail about your skills.'}`

      setMessages(prev => [...prev, { role: 'assistant', content: finalMessage }])
      onProfileComplete?.({ profile, opportunities, country: country_code })
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

  const handleSend = async () => {
    if (!input.trim() || loading) return

    // Hotkey: "Test: Amara" / "Test: Bern" / "Test: Cal" — skip the chat, run the chain directly.
    const persona = matchTestCommand(input)
    if (persona) {
      const userMessage = { role: 'user', content: input.trim() }
      setMessages(prev => [
        ...prev,
        userMessage,
        { role: 'assistant', content: `Loading test persona: ${persona.label}` },
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
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type your message... or 'Test: Amara' / 'Test: Bern' / 'Test: Cal'"
          disabled={loading}
          className="flex-1 border rounded-lg p-3 disabled:bg-gray-100"
        />
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
