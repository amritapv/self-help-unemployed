import { useState } from 'react'
import ChatView from './ChatView'
import ProfileCard from './ProfileCard'
import OpportunityList from './OpportunityList'

function App() {
  const [country, setCountry] = useState('GH')
  const [skillsProfile, setSkillsProfile] = useState(null)
  const [opportunities, setOpportunities] = useState(null)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white p-4">
        <h1 className="text-xl font-bold">UNMAPPED</h1>
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="mt-2 text-black rounded p-1"
        >
          <option value="GH">Ghana</option>
          <option value="IN">India</option>
        </select>
      </header>

      <main className="max-w-2xl mx-auto p-4">
        {!skillsProfile ? (
          <ChatView country={country} onProfileComplete={setSkillsProfile} />
        ) : !opportunities ? (
          <>
            <ProfileCard profile={skillsProfile} />
            <button
              onClick={() => {/* TODO: fetch opportunities */}}
              className="w-full mt-4 bg-blue-600 text-white p-3 rounded"
            >
              Find Opportunities
            </button>
            <button
              onClick={() => setSkillsProfile(null)}
              className="w-full mt-2 border border-gray-300 text-gray-600 p-3 rounded"
            >
              Start Over
            </button>
          </>
        ) : (
          <OpportunityList opportunities={opportunities} />
        )}
      </main>
    </div>
  )
}

export default App
