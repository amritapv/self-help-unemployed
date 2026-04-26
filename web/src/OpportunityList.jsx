// Job Opportunities screen — rendered when the user clicks the "Job Opportunities" tab.
// One card per opportunity with the matcher's full prose fields.

function OpportunityList({ opportunities }) {
  if (!opportunities?.length) {
    return (
      <div className="bg-white rounded-lg shadow p-5 text-sm text-gray-600">
        No opportunities yet — the matcher couldn't surface a top 3 from this profile.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">Top {opportunities.length} opportunities for you</h2>
      {opportunities.map((opp, i) => (
        <article key={i} className="bg-white rounded-lg shadow p-5">
          <header className="flex items-baseline justify-between mb-2 gap-3 flex-wrap">
            <h3 className="font-semibold text-gray-900">
              <span className="text-blue-600 me-2">{i + 1}.</span>
              {opp.title}
            </h3>
            {opp.opportunity_type && (
              <span className="text-xs uppercase tracking-wide text-gray-500">
                {opp.opportunity_type.replace(/_/g, ' ')}
              </span>
            )}
          </header>

          {opp.employer_or_path && (
            <p className="text-sm text-gray-500 mb-3">{opp.employer_or_path}</p>
          )}

          <p className="text-gray-700 mb-3 leading-relaxed">
            {opp.fit_explanation}
          </p>

          <div className="grid gap-2 text-sm sm:grid-cols-2 mb-3">
            <div className="text-blue-700">
              <span className="font-medium me-2">Wage</span>
              {opp.wage_range}
            </div>
            <div className="text-green-700">
              <span className="font-medium me-2">Outlook</span>
              {opp.sector_growth || opp.sector_growth_signal}
            </div>
          </div>

          {opp.skill_gap && (
            <p className="text-sm text-amber-700 mb-2">
              <span className="font-medium me-2">Gap</span>
              {opp.skill_gap}
            </p>
          )}
          {opp.next_step && (
            <p className="text-sm text-gray-800">
              <span className="font-medium me-2">Next step</span>
              {opp.next_step}
            </p>
          )}
        </article>
      ))}
    </div>
  )
}

export default OpportunityList
