function RiskDisplay({ risk }) {
  const riskColor = {
    low: 'bg-green-100 text-green-800',
    moderate: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800'
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mt-4">
      <h2 className="text-lg font-bold mb-3">AI Readiness Check</h2>
      <div className={`inline-block px-3 py-1 rounded ${riskColor[risk?.overall_risk] || riskColor.moderate}`}>
        {risk?.overall_risk || 'moderate'} automation risk
      </div>
      <p className="text-gray-700 my-3">{risk?.plain_language_summary}</p>

      {risk?.durable_skills?.length > 0 && (
        <div className="mb-3">
          <h3 className="font-semibold text-green-700">Durable Skills</h3>
          <p className="text-sm text-gray-600">{risk.durable_skills.join(', ')}</p>
        </div>
      )}

      {risk?.adjacent_skills_for_resilience?.length > 0 && (
        <div>
          <h3 className="font-semibold">Skills to Build</h3>
          <ul className="text-sm text-gray-600 list-disc ml-4">
            {risk.adjacent_skills_for_resilience.map((skill, i) => <li key={i}>{skill}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

export default RiskDisplay
