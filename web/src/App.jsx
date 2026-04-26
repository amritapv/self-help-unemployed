import { useState } from 'react'
import ChatView from './ChatView'
import ProfileCard from './ProfileCard'
import OpportunityList from './OpportunityList'
import PolicymakerView from './PolicymakerView'

const API_URL = 'http://localhost:8000'

function App() {
  const [mode, setMode] = useState('citizen')  // 'citizen' | 'policymaker'
  const [country, setCountry] = useState('GH')
  const [skillsProfile, setSkillsProfile] = useState(null)
  const [opportunities, setOpportunities] = useState(null)
  const [matching, setMatching] = useState(false)
  const [matchError, setMatchError] = useState(null)

  const handleFindOpportunities = async () => {
    setMatching(true)
    setMatchError(null)
    try {
      const response = await fetch(`${API_URL}/match-opportunities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skills_profile: skillsProfile,
          country_code: country,
        }),
      })
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`)
      }
      const data = await response.json()
      setOpportunities(data.opportunities ?? [])
    } catch (error) {
      console.error('Opportunity match error:', error)
      setMatchError("Couldn't load opportunities. Please try again.")
    } finally {
      setMatching(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-xl font-bold tracking-tight">UNMAPPED</h1>
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/40 rounded-lg p-1 flex gap-1 text-sm">
              <button
                onClick={() => setMode('citizen')}
                className={`px-3 py-1 rounded-md transition ${mode === 'citizen' ? 'bg-white text-blue-700 font-medium' : 'text-white/90 hover:text-white'}`}
              >
                Citizen
              </button>
              <button
                onClick={() => setMode('policymaker')}
                className={`px-3 py-1 rounded-md transition ${mode === 'policymaker' ? 'bg-white text-blue-700 font-medium' : 'text-white/90 hover:text-white'}`}
              >
                Policymaker
              </button>
            </div>
            {mode === 'citizen' && (
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="text-black rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-white"
              >
                <option value="GH">Ghana</option>
                <option value="IN">India</option>
              </select>
            )}
          </div>
        </div>
      </header>

      {mode === 'policymaker' ? (
        <PolicymakerView />
      ) : (
      <main className="max-w-2xl mx-auto p-4">
        {!skillsProfile ? (
          <ChatView country={country} onProfileComplete={setSkillsProfile} />
        ) : !opportunities ? (
          <>
            <ProfileCard profile={skillsProfile} />
            <button
              onClick={handleFindOpportunities}
              disabled={matching}
              className="w-full mt-4 bg-blue-600 text-white p-3 rounded disabled:opacity-50"
            >
              {matching ? 'Finding opportunities...' : 'Find Opportunities'}
            </button>
            {matchError && (
              <p className="mt-2 text-sm text-red-600">{matchError}</p>
            )}
            <button
              onClick={() => setSkillsProfile(null)}
              disabled={matching}
              className="w-full mt-2 border border-gray-300 text-gray-600 p-3 rounded disabled:opacity-50"
            >
              Start Over
            </button>
          </>
        ) : (
          <OpportunityList opportunities={opportunities} />
        )}
      </main>
      )}
    </div>
  )
}

export default App
