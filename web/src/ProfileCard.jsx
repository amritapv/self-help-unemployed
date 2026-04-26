// Skills Profile screen — rendered when the user clicks the "Skills Profile" tab.
// Surfaces everything Module 01 + Module 02 produced.

const VERDICT_STYLE = {
  mostly_safe: 'bg-green-100 text-green-800 border-green-200',
  watch:       'bg-amber-100 text-amber-800 border-amber-200',
  act_now:     'bg-red-100 text-red-800 border-red-200',
  unknown:     'bg-gray-100 text-gray-700 border-gray-200',
}

function ProfileCard({ profile }) {
  if (!profile) return null

  const risk = profile.automation_risk

  return (
    <div className="space-y-6">
      {/* Portable summary */}
      <section className="bg-white rounded-lg shadow p-5">
        <h2 className="text-lg font-bold mb-2">Your Skills Profile</h2>
        <p className="text-gray-700 leading-relaxed">{profile.portable_summary}</p>
      </section>

      {/* Matched occupations */}
      {profile.matched_occupations?.length > 0 && (
        <section className="bg-white rounded-lg shadow p-5">
          <h3 className="font-semibold mb-3">Matched roles</h3>
          <ul className="space-y-1">
            {profile.matched_occupations.map((occ, i) => (
              <li key={i} className="flex items-start justify-between text-sm">
                <span className="text-gray-800">{occ.title}</span>
                {occ.confidence && (
                  <span className="text-xs uppercase tracking-wide text-gray-500 ms-3">
                    {String(occ.confidence)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Skills */}
      {profile.skills?.length > 0 && (
        <section className="bg-white rounded-lg shadow p-5">
          <h3 className="font-semibold mb-3">Skills</h3>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map((s, i) => (
              <span
                key={i}
                className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
              >
                {s.skill_name}
                {s.level && (
                  <span className="text-blue-600/70 text-xs ms-2">{s.level}</span>
                )}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Languages + Education */}
      {(profile.languages?.length > 0 || profile.education_level) && (
        <section className="bg-white rounded-lg shadow p-5 space-y-3">
          {profile.languages?.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Languages</h3>
              <p className="text-sm text-gray-700">
                {profile.languages
                  .map((l) => `${l.language} (${l.proficiency})`)
                  .join(', ')}
              </p>
            </div>
          )}
          {profile.education_level && (
            <div>
              <h3 className="font-semibold mb-1">Education</h3>
              <p className="text-sm text-gray-700">
                {profile.education_level.local_credential ||
                  profile.education_level.local_equivalent ||
                  profile.education_level.description}
                {profile.education_level.isced_level && (
                  <span className="text-gray-400 ms-2">
                    (ISCED {profile.education_level.isced_level})
                  </span>
                )}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Automation risk */}
      {risk && risk.verdict && risk.verdict !== 'unknown' && (
        <section className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Automation outlook</h3>
            <span
              className={`text-xs uppercase tracking-wide font-medium border rounded-full px-3 py-1 ${
                VERDICT_STYLE[risk.verdict] || VERDICT_STYLE.unknown
              }`}
            >
              {risk.verdict_label || risk.verdict}
            </span>
          </div>
          <p className="text-gray-700 leading-relaxed mb-4">
            {risk.plain_language_summary}
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            {risk.machines_handling?.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">
                  Machines are getting better at
                </h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {risk.machines_handling.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
            {risk.still_needs_you?.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">
                  Still needs you
                </h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {risk.still_needs_you.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
            {risk.worth_learning?.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">
                  Worth picking up
                </h4>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  {risk.worth_learning.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  )
}

export default ProfileCard
