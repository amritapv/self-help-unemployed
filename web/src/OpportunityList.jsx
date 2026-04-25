function OpportunityList({ opportunities }) {
  return (
    <div>
      <h2 className="text-lg font-bold mb-4">Opportunities For You</h2>
      <div className="space-y-4">
        {opportunities?.map((opp, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4">
            <h3 className="font-bold">{opp.title}</h3>
            <p className="text-sm text-gray-500">{opp.employer_or_path}</p>
            {/* Econometric signals - visible per PRD requirement */}
            <div className="my-2 text-sm">
              <div className="text-green-700">{opp.sector_growth_signal}</div>
              <div className="text-blue-700">{opp.wage_range}</div>
            </div>
            <p className="text-gray-700 text-sm">{opp.fit_explanation}</p>
            {opp.skill_gap && <p className="text-orange-600 text-sm mt-2">Gap: {opp.skill_gap}</p>}
            <p className="text-sm mt-2 font-medium">Next step: {opp.next_step}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default OpportunityList
