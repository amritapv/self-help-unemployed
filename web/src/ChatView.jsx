import { useState } from 'react'

const QUESTIONS = [
  "What's your highest level of education?",
  "What work have you done? Include informal work, side jobs, anything.",
  "What skills have you taught yourself?",
  "What languages do you speak?",
]

function ChatView({ country, onProfileComplete }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! I'm here to help you understand your skills. " + QUESTIONS[0] }
  ])
  const [input, setInput] = useState('')
  const [questionIndex, setQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState([])

  const handleSend = async () => {
    if (!input.trim()) return

    const newMessages = [...messages, { role: 'user', content: input }]
    const newAnswers = [...answers, input]
    setMessages(newMessages)
    setAnswers(newAnswers)
    setInput('')

    if (questionIndex < QUESTIONS.length - 1) {
      setQuestionIndex(questionIndex + 1)
      setMessages([...newMessages, { role: 'assistant', content: QUESTIONS[questionIndex + 1] }])
    } else {
      setMessages([...newMessages, { role: 'assistant', content: 'Analyzing your skills...' }])
      // TODO: POST to /assess-skills and call onProfileComplete(profile)
    }
  }

  return (
    <div className="flex flex-col h-[70vh]">
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.map((msg, i) => (
          <div key={i} className={`p-3 rounded ${msg.role === 'user' ? 'bg-blue-100 ml-8' : 'bg-gray-200 mr-8'}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <div className="flex gap-2 p-4 border-t">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type your answer..."
          className="flex-1 border rounded p-2"
        />
        <button onClick={handleSend} className="bg-blue-600 text-white px-4 rounded">Send</button>
      </div>
    </div>
  )
}

export default ChatView
