import { useEffect, useState } from 'react'
import ChatView from './ChatView'
import ProfileCard from './ProfileCard'
import OpportunityList from './OpportunityList'
import { LANGUAGES, t, isRTL } from './i18n'

function App() {
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

  return (
    <div className="min-h-screen bg-gray-50" dir={rtl ? 'rtl' : 'ltr'}>
      <header className="bg-blue-600 text-white p-4">
        <h1 className="text-xl font-bold">{t(language, 'headerTitle')}</h1>
        <div className="mt-2 flex flex-wrap gap-2">
          <label className="flex flex-col text-sm">
            <span className="text-xs opacity-80">{t(language, 'countryLabel')}</span>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="text-black rounded p-1"
            >
              <option value="GH">Ghana</option>
              <option value="IN">India</option>
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="text-xs opacity-80">{t(language, 'languageLabel')}</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="text-black rounded p-1"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.native}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4">
        {!skillsProfile ? (
          <ChatView
            country={country}
            language={language}
            onProfileComplete={setSkillsProfile}
          />
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
