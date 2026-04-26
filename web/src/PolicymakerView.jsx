import { useEffect, useMemo, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const API_URL = 'http://localhost:8000'

const RISK_COLORS = {
  low: '#22c55e',
  moderate: '#f59e0b',
  high: '#ef4444',
}

const EDUCATION_COLORS = ['#1e3a8a', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe']

const ISCED_LABELS = {
  ISCED_1: 'Primary',
  ISCED_2: 'Lower secondary',
  ISCED_3: 'Upper secondary',
  ISCED_4: 'Post-secondary',
  ISCED_5: 'Short-cycle tertiary',
  ISCED_6: "Bachelor's",
  ISCED_7: "Master's+",
}

function formatPct(v, digits = 0) {
  if (v == null) return '—'
  return `${(v * 100).toFixed(digits)}%`
}

function formatSector(s) {
  return s ? s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : ''
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function Kpi({ label, value, sublabel, accent = 'text-gray-900' }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="text-xs uppercase tracking-wider text-gray-500 font-medium">{label}</div>
      <div className={`mt-1 text-3xl font-bold ${accent}`}>{value}</div>
      {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
    </div>
  )
}

// ── Card wrapper ──────────────────────────────────────────────────────────────

function Card({ title, subtitle, children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 shadow-sm p-5 ${className}`}>
      <div className="mb-4">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

// ── Charts ────────────────────────────────────────────────────────────────────

function TopSkillsChart({ skills }) {
  const data = (skills || []).slice(0, 8).map(s => ({ ...s, skill: s.skill }))
  if (!data.length) return <Empty />

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis type="number" stroke="#64748b" fontSize={11} />
        <YAxis
          type="category"
          dataKey="skill"
          stroke="#64748b"
          fontSize={11}
          width={150}
          tick={{ textAnchor: 'end' }}
        />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
          formatter={(value, _, p) => [`${value} profiles (${formatPct(p.payload.pct, 1)})`, 'Count']}
        />
        <Bar dataKey="count" fill="#2563eb" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function EducationDonut({ levels }) {
  const data = Object.entries(levels || {})
    .map(([k, v]) => ({ name: ISCED_LABELS[k] || k, code: k, value: v }))
    .sort((a, b) => a.code.localeCompare(b.code))
  if (!data.length) return <Empty />

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={95}
          paddingAngle={2}
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={EDUCATION_COLORS[i % EDUCATION_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => formatPct(v, 1)} contentStyle={{ borderRadius: 8, fontSize: 12 }} />
        <Legend
          iconType="circle"
          wrapperStyle={{ fontSize: 11 }}
          formatter={(value, entry) => `${value} ${formatPct(entry.payload.value, 0)}`}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

function AutomationBars({ exposure }) {
  const order = ['high', 'moderate', 'low']
  const rows = order.map(band => ({
    band,
    pct: exposure?.[`${band}_risk`]?.pct || 0,
    occupations: exposure?.[`${band}_risk`]?.top_occupations || [],
  }))

  return (
    <div className="space-y-3">
      {rows.map(({ band, pct, occupations }) => (
        <div key={band}>
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-sm font-medium capitalize" style={{ color: RISK_COLORS[band] }}>
              {band} risk
            </span>
            <span className="text-sm text-gray-700 tabular-nums">{formatPct(pct, 1)}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${(pct * 100).toFixed(1)}%`, backgroundColor: RISK_COLORS[band] }}
            />
          </div>
          {occupations.length > 0 && (
            <div className="text-xs text-gray-500 mt-1">
              Top: {occupations.slice(0, 3).join(' · ')}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function SectorGrowthChart({ econometric }) {
  const data = Object.entries(econometric?.sector_growth || {})
    .filter(([, v]) => v != null)
    .map(([sector, growth]) => ({ sector: formatSector(sector), growth: growth * 100 }))
    .sort((a, b) => b.growth - a.growth)

  if (!data.length) return <Empty />

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ bottom: 50, right: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="sector"
          stroke="#64748b"
          fontSize={10}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          stroke="#64748b"
          fontSize={11}
          tickFormatter={v => `${v}%`}
        />
        <Tooltip
          formatter={v => [`${v.toFixed(1)}% per year`, 'Growth']}
          contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
        />
        <Bar dataKey="growth" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function Empty() {
  return (
    <div className="h-[300px] flex items-center justify-center text-sm text-gray-400">
      No data for this filter
    </div>
  )
}

// ── Filter row ────────────────────────────────────────────────────────────────

function FilterRow({ meta, country, region, sector, onChange }) {
  const countryEntry = meta?.countries?.find(c => c.code === country)
  const regions = countryEntry?.regions || []
  const sectors = countryEntry?.sectors || []

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap items-end gap-3">
      <Selector
        label="Country"
        value={country}
        onChange={v => onChange({ country: v, region: '', sector })}
      >
        {(meta?.countries || []).map(c => (
          <option key={c.code} value={c.code}>{c.name}</option>
        ))}
      </Selector>

      <Selector
        label="Region"
        value={region}
        onChange={v => onChange({ country, region: v, sector })}
      >
        <option value="">All regions</option>
        {regions.map(r => (
          <option key={r.code} value={r.code}>{r.name}</option>
        ))}
      </Selector>

      <Selector
        label="Sector"
        value={sector}
        onChange={v => onChange({ country, region, sector: v })}
      >
        <option value="">All sectors</option>
        {sectors.map(s => (
          <option key={s} value={s}>{formatSector(s)}</option>
        ))}
      </Selector>

      {(region || sector) && (
        <button
          onClick={() => onChange({ country, region: '', sector: '' })}
          className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-50"
        >
          Reset filters
        </button>
      )}
    </div>
  )
}

function Selector({ label, value, onChange, children }) {
  return (
    <label className="flex flex-col text-xs font-medium text-gray-600 uppercase tracking-wider">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm font-normal text-gray-900 normal-case tracking-normal min-w-[160px] focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {children}
      </select>
    </label>
  )
}

// ── Skill gaps list ──────────────────────────────────────────────────────────

function SkillGaps({ gaps }) {
  return (
    <Card title="Biggest skill gaps" subtitle="Most-cited barriers across opportunities in this cohort">
      {(gaps?.biggest_skill_gaps?.length ?? 0) === 0 ? (
        <Empty />
      ) : (
        <ul className="space-y-2">
          {gaps.biggest_skill_gaps.map((g, i) => (
            <li key={i} className="flex gap-3 items-start">
              <span className="mt-1 inline-block w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
              <span className="text-sm text-gray-700">{g}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

// ── Onboarding instructions ───────────────────────────────────────────────────

function OnboardingPanel({ onCountryUpserted }) {
  const [downloading, setDownloading] = useState(false)

  const handleDownloadTemplate = async () => {
    setDownloading(true)
    try {
      const r = await fetch(`${API_URL}/admin/countries/template?reference=GH`)
      const json = await r.json()
      const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'country-template.json'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  const curlExample = `curl -X POST http://localhost:8000/admin/countries \\
  -H "Content-Type: application/json" \\
  -d @country-NG.json`

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900">Onboard or update a country</h2>
        <p className="text-sm text-gray-600 mt-1 max-w-2xl">
          The platform is fully data-driven. To add a new country (or revise an existing
          one) you POST a single JSON document to the admin endpoint. No code change,
          no restart — every endpoint picks up the change on the next request.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-4">How it works</h3>
        <ol className="space-y-4 text-sm text-gray-700">
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">1</span>
            <div className="flex-1">
              <div className="font-medium text-gray-900">Download the template</div>
              <div className="text-gray-600 mt-0.5">A pre-filled Ghana block to copy and edit. Same shape the platform uses internally.</div>
              <button
                onClick={handleDownloadTemplate}
                disabled={downloading}
                className="mt-2 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
              >
                {downloading ? 'Preparing…' : 'Download country-template.json'}
              </button>
            </div>
          </li>

          <li className="flex gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">2</span>
            <div className="flex-1">
              <div className="font-medium text-gray-900">Edit the JSON for your country</div>
              <div className="text-gray-600 mt-0.5">
                Fill in the required fields below. Anything not listed here is optional but preserved (e.g.{' '}
                <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">training_pathways</code>,{' '}
                <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">localization</code>).
              </div>
            </div>
          </li>

          <li className="flex gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">3</span>
            <div className="flex-1">
              <div className="font-medium text-gray-900">POST it to the admin endpoint</div>
              <div className="text-gray-600 mt-0.5">Validation tells you what's missing or malformed.</div>
              <pre className="mt-2 bg-gray-900 text-gray-100 text-xs p-3 rounded-lg overflow-x-auto">
                <code>{curlExample}</code>
              </pre>
            </div>
          </li>

          <li className="flex gap-3">
            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">4</span>
            <div className="flex-1">
              <div className="font-medium text-gray-900">Refresh — your country is live</div>
              <div className="text-gray-600 mt-0.5">
                It appears in the Citizen flow's country dropdown and in this dashboard's filters immediately.
              </div>
            </div>
          </li>
        </ol>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-3">Required fields</h3>
        <dl className="grid md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <FieldDoc name="country_code" desc='Two-letter uppercase ISO 3166-1, e.g. "NG"' />
          <FieldDoc name="country_name" desc='Display name, e.g. "Nigeria"' />
          <FieldDoc name="language" desc='{"primary": "en", "local": ["ha", "yo"]}' />
          <FieldDoc name="currency" desc='{"code": "NGN", "symbol": "₦"}' />
          <FieldDoc name="regions" desc='List of {code, name, type} (type: urban_metro | rural_ag | mixed)' />
          <FieldDoc name="sectors" desc="Map of slug → {growth_annual, share_employment, informal_share}. Slugs must be stable across countries." />
          <FieldDoc name="wage_data" desc="Map of 4-digit ISCO code → {min, max, median, sector}. ISCO codes ideally have entries in frey_osborne.json; if not, the major group falls back automatically." />
          <FieldDoc name="automation_calibration" desc='{"infrastructure_factor": 0.4–1.2, "rationale": "..."} — multiplies Frey-Osborne probabilities to country context.' />
          <FieldDoc name="opportunity_types" desc='Subset of: formal_employment, self_employment, gig, apprenticeship, training_pathway' />
          <FieldDoc name="education_taxonomy" desc="ISCED levels mapped to local credential names. Same shape as the GH/IN templates." />
          <FieldDoc name="demographics" desc='{youth_unemployment_rate, informality_rate, urbanization_rate, median_age, youth_pop_share}' />
        </dl>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-900">
        <div className="font-semibold mb-1">Notes</div>
        <ul className="space-y-1 list-disc pl-5">
          <li>UI translations for a new primary language still live in <code className="text-xs bg-amber-100 px-1 rounded">web/src/i18n.js</code> — drop a new entry there if you want native-language UI strings. The platform falls back to English otherwise.</li>
          <li>Sector slugs (<code className="text-xs bg-amber-100 px-1 rounded">ict</code>, <code className="text-xs bg-amber-100 px-1 rounded">renewable_energy</code>, etc.) are intentionally shared across countries so cross-country aggregation works. Reuse existing slugs where possible.</li>
          <li>The endpoint is open in this build. Don't expose it to the public internet without auth.</li>
        </ul>
      </div>
    </div>
  )
}

function FieldDoc({ name, desc }) {
  return (
    <div>
      <dt className="font-mono text-xs text-blue-700 font-semibold">{name}</dt>
      <dd className="text-gray-600 mt-0.5">{desc}</dd>
    </div>
  )
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function PolicymakerView() {
  const [tab, setTab] = useState('dashboard')  // 'dashboard' | 'onboard'
  const [meta, setMeta] = useState(null)
  const [filters, setFilters] = useState({ country: 'GH', region: '', sector: '' })
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load country metadata once
  useEffect(() => {
    fetch(`${API_URL}/meta/countries`)
      .then(r => r.json())
      .then(setMeta)
      .catch(e => setError(`Couldn't load metadata: ${e.message}`))
  }, [])

  // Fetch report on filter change
  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ country: filters.country })
    if (filters.region) params.set('region', filters.region)
    if (filters.sector) params.set('sector', filters.sector)

    fetch(`${API_URL}/report?${params}`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(setReport)
      .catch(e => setError(`Couldn't load report: ${e}`))
      .finally(() => setLoading(false))
  }, [filters])

  const econ = report?.econometric_signals
  const topGrowthSector = useMemo(() => {
    const entries = Object.entries(econ?.sector_growth || {}).filter(([, v]) => v != null)
    if (!entries.length) return null
    const [name] = entries.reduce((a, b) => (a[1] > b[1] ? a : b))
    return name
  }, [econ])

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-5">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {tab === 'dashboard' ? 'Policymaker dashboard' : 'Configure your country'}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {tab === 'dashboard'
              ? 'Aggregate skills, automation exposure, and opportunity gaps across assessed youth profiles.'
              : 'Onboard a new country or update an existing one — no code change required.'}
          </p>
        </div>
        <div className="bg-gray-100 rounded-lg p-1 flex gap-1 text-sm">
          <button
            onClick={() => setTab('dashboard')}
            className={`px-4 py-1.5 rounded-md transition ${tab === 'dashboard' ? 'bg-white text-gray-900 font-medium shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setTab('onboard')}
            className={`px-4 py-1.5 rounded-md transition ${tab === 'onboard' ? 'bg-white text-gray-900 font-medium shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            Onboard country
          </button>
        </div>
      </div>

      {tab === 'onboard' ? (
        <OnboardingPanel />
      ) : (
        <DashboardBody
          meta={meta}
          filters={filters}
          setFilters={setFilters}
          report={report}
          loading={loading}
          error={error}
          econ={econ}
          topGrowthSector={topGrowthSector}
        />
      )}
    </div>
  )
}

function DashboardBody({ meta, filters, setFilters, report, loading, error, econ, topGrowthSector }) {
  return (
    <>
      <FilterRow
        meta={meta}
        country={filters.country}
        region={filters.region}
        sector={filters.sector}
        onChange={setFilters}
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">{error}</div>
      )}

      {loading && !report ? (
        <div className="text-center text-gray-400 py-12">Loading…</div>
      ) : report && (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Kpi
              label="Profiles assessed"
              value={report.report_meta?.profiles_assessed ?? 0}
              sublabel={report.report_meta?.region || report.report_meta?.country}
            />
            <Kpi
              label="Youth unemployment"
              value={formatPct(econ?.youth_unemployment, 1)}
              sublabel="National rate"
              accent="text-amber-600"
            />
            <Kpi
              label="Informality rate"
              value={formatPct(econ?.informality_rate, 0)}
              sublabel="Share of jobs informal"
              accent="text-amber-600"
            />
            <Kpi
              label="Top growth sector"
              value={topGrowthSector ? formatSector(topGrowthSector) : '—'}
              sublabel={topGrowthSector ? formatPct(econ.sector_growth[topGrowthSector], 1) + ' / yr' : ''}
              accent="text-emerald-600"
            />
          </div>

          <div className="grid lg:grid-cols-2 gap-5">
            <Card title="Top skills in cohort" subtitle="Most common skills across assessed profiles">
              <TopSkillsChart skills={report.skills_distribution?.top_skills} />
            </Card>
            <Card title="Education distribution" subtitle="Share of profiles by ISCED level">
              <EducationDonut levels={report.skills_distribution?.education_levels} />
            </Card>
            <Card title="Automation exposure" subtitle="Calibrated risk band shares + leading occupations">
              <AutomationBars exposure={report.automation_exposure} />
            </Card>
            <Card title="Sector growth" subtitle="Annual growth rate, all sectors">
              <SectorGrowthChart econometric={econ} />
            </Card>
          </div>

          <SkillGaps gaps={report.opportunity_gaps} />
        </>
      )}
    </>
  )
}
