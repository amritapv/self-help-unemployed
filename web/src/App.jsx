import { useEffect, useState } from 'react'
import ChatView from './ChatView'
import ProfileCard from './ProfileCard'
import OpportunityList from './OpportunityList'
import PolicymakerView from './PolicymakerView'
import { LANGUAGES, t, isRTL } from './i18n'

function App() {
  const [mode, setMode] = useState('citizen')          // 'citizen' | 'policymaker'
  const [view, setView] = useState('chat')             // 'chat' | 'skills' | 'opps'
  const [country, setCountry] = useState('GH')
  const [language, setLanguage] = useState(
    () => localStorage.getItem('unmapped_language') || 'en'
  )
  const [skillsProfile, setSkillsProfile] = useState(null)
  const [opportunities, setOpportunities] = useState(null)

  useEffect(() => {
    localStorage.setItem('unmapped_language', language)
  }, [language])

  const rtl = isRTL(language)
  const hasResults = !!skillsProfile

  const tabs = [
    { id: 'chat',   label: 'Chat',             enabled: true },
    { id: 'skills', label: 'Skills Profile',   enabled: hasResults },
    { id: 'opps',   label: 'Job Opportunities', enabled: hasResults && Array.isArray(opportunities) && opportunities.length > 0 },
  ]

  return (
    <div className="min-h-screen bg-gray-50" dir={rtl ? 'rtl' : 'ltr'}>
      <header className="bg-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-xl font-bold tracking-tight">{t(language, 'headerTitle')}</h1>
          <div className="flex items-center gap-3 flex-wrap">
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
                aria-label={t(language, 'countryLabel')}
              >
                <option value="GH">Ghana</option>
                <option value="IN">India</option>
              </select>
            )}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="text-black rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-white"
              aria-label={t(language, 'languageLabel')}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.native}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {mode === 'policymaker' ? (
        <PolicymakerView />
      ) : (
        <main className="max-w-3xl mx-auto p-4">
          {/* Tab strip — Skills + Opps unlock once the assessment lands. */}
          <div className="flex gap-2 mb-4 border-b border-gray-200">
            {tabs.map((tab) => {
              const active = view === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => tab.enabled && setView(tab.id)}
                  disabled={!tab.enabled}
                  className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
                    active
                      ? 'border-blue-600 text-blue-700'
                      : tab.enabled
                        ? 'border-transparent text-gray-600 hover:text-gray-900'
                        : 'border-transparent text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Chat is always mounted (so state persists). The other tabs render only when ready. */}
          <div className={view === 'chat' ? '' : 'hidden'}>
            <ChatView
              country={country}
              language={language}
              onProfileComplete={({ profile, opportunities }) => {
                setSkillsProfile(profile)
                setOpportunities(opportunities || [])
              }}
            />
          </div>
          {view === 'skills' && skillsProfile && (
            <ProfileCard profile={skillsProfile} />
          )}
          {view === 'opps' && Array.isArray(opportunities) && (
            <OpportunityList opportunities={opportunities} />
          )}
        </main>
      )}
    </div>
  )
}

export default App
