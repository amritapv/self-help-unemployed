import { useEffect, useState } from 'react'
import ChatView from './ChatView'
import PolicymakerView from './PolicymakerView'
import { LANGUAGES, t, isRTL } from './i18n'

function App() {
  const [mode, setMode] = useState('citizen')  // 'citizen' | 'policymaker'
  const [country, setCountry] = useState('GH')
  const [language, setLanguage] = useState(
    () => localStorage.getItem('unmapped_language') || 'en'
  )

  useEffect(() => {
    localStorage.setItem('unmapped_language', language)
  }, [language])

  const rtl = isRTL(language)

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
        <main className="max-w-2xl mx-auto p-4">
          <ChatView
            country={country}
            language={language}
            onProfileComplete={() => { /* ChatView renders top-5 opportunities inline */ }}
          />
        </main>
      )}
    </div>
  )
}

export default App
