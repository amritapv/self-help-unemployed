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

// ── Main view ─────────────────────────────────────────────────────────────────

export default function PolicymakerView() {
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Policymaker dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Aggregate skills, automation exposure, and opportunity gaps across assessed youth profiles.
        </p>
      </div>

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
    </div>
  )
}
