function ProfileCard({ profile }) {
  // Handle the human_readable text (pre-formatted from backend)
  if (profile.human_readable) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <pre className="whitespace-pre-wrap font-sans text-gray-700 text-sm leading-relaxed">
          {profile.human_readable}
        </pre>
      </div>
    )
  }

  // Fallback to structured display
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-bold mb-3">Your Skills Profile</h2>
      <p className="text-gray-700 mb-4">{profile.portable_summary}</p>

      <div className="mb-3">
        <h3 className="font-semibold">Matched Occupations</h3>
        {profile.matched_occupations?.map((occ, i) => (
          <div key={i} className="text-sm text-gray-600">
            {occ.title} (ISCO {occ.isco_code})
            {occ.confidence && <span className="text-gray-400 ml-2">[{occ.confidence}]</span>}
          </div>
        ))}
      </div>

      <div className="mb-3">
        <h3 className="font-semibold">Skills</h3>
        <div className="flex flex-wrap gap-2">
          {profile.skills?.map((skill, i) => (
            <span key={i} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
              {skill.skill_name}
            </span>
          ))}
        </div>
      </div>

      <div className="mb-3">
        <h3 className="font-semibold">Languages</h3>
        {profile.languages?.map((lang, i) => (
          <span key={i} className="text-sm text-gray-600 mr-2">
            {lang.language} ({lang.proficiency})
          </span>
        ))}
      </div>

      <div className="text-sm text-gray-500">
        Education: {profile.education_level?.local_credential || profile.education_level?.description}
        {profile.education_level?.isced_level && ` (ISCED ${profile.education_level.isced_level})`}
      </div>
    </div>
  )
}

export default ProfileCard
