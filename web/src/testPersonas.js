// Canned profiles for "Test: <Name>" shortcut. Each persona is a fully
// pre-collected SkillsAssessmentRequest body — bypasses the chat back-and-forth
// and goes straight to /assess-skills + /match-opportunities.
//
// `bio` is shown in the chat as a profile card before the assessment runs,
// so the user can see who they're testing as.
//
// To add a persona: drop another entry here keyed by lowercase name.

export const TEST_PERSONAS = {
  amara: {
    label: 'Amara — Ghana, mobile phone repair (low-risk technical trade)',
    expectedVerdict: 'mostly_safe',
    bio: {
      name: 'Amara',
      age: 22,
      city: 'Accra',
      country: 'Ghana',
      tagline: 'The self-made repair tech.',
      headline: 'Runs her own phone repair shop in Accra. Self-taught coder.',
      backstory:
        "Five years in the trade. Started by fixing her cousin's cracked screen, " +
        'now has a steady customer base around Osu. Picks up Python on YouTube ' +
        'in the quiet hours and has been teaching her two younger siblings the ropes.',
    },
    payload: {
      country_code: 'GH',
      region: 'greater_accra',
      education: 'I completed my WASSCE (secondary school) in 2019.',
      experience:
        "I've been running my own phone repair shop in Accra for about five years. " +
        'I fix screens, replace batteries, diagnose circuit problems, and sometimes ' +
        'recover data from water-damaged phones. I taught two younger siblings the basics.',
      skills_self_reported:
        'Soldering, circuit diagnostics, screen replacement, basic Python from YouTube, ' +
        'customer service, teaching apprentices, cash handling.',
      additional_info:
        'I speak English fluently, Twi natively, and some Ga.',
    },
  },
  bern: {
    label: 'Bern — India, office clerk (high-risk clerical work)',
    expectedVerdict: 'act_now',
    bio: {
      name: 'Bern',
      age: 25,
      city: 'Mumbai',
      country: 'India',
      tagline: 'The bright clerk feeling the squeeze.',
      headline: 'Data entry clerk at a small Mumbai accounting firm. BCom degree.',
      backstory:
        'Three years on Tally — invoices, ledgers, client records. Knows Excel cold. ' +
        "Quick at filing and great at handling phone queries. Lately he's been hearing " +
        "the firm talk about software that might do most of his day's work, and " +
        "he's wondering what comes next.",
    },
    payload: {
      country_code: 'IN',
      region: 'maharashtra',
      education: "I have a Bachelor's in Commerce (BCom) from Mumbai University, completed in 2021.",
      experience:
        'Three years as a data entry clerk at a small accounting firm in Mumbai. ' +
        'My day is mostly entering invoices into Tally, managing client records, ' +
        'filing documents, scheduling appointments, and handling phone enquiries. ' +
        'I also reconcile small ledgers at month-end.',
      skills_self_reported:
        'Typing 60+ wpm, MS Office (Word/Excel), basic Excel formulas like VLOOKUP and SUMIF, ' +
        'Tally accounting software, English correspondence, document filing, basic bookkeeping.',
      additional_info:
        'I speak Hindi natively, Marathi fluently, and English well enough to write emails.',
    },
  },
  cal: {
    label: 'Cal — Ghana, electronics retail (moderate-risk retail work)',
    expectedVerdict: 'watch',
    bio: {
      name: 'Cal',
      age: 23,
      city: 'Kumasi',
      country: 'Ghana',
      tagline: 'The natural seller in a shifting market.',
      headline: "Sells electronics at his uncle's shop in Kumasi.",
      backstory:
        'Three years on the floor — TVs, phones, fridges, small appliances. ' +
        'Knows the products inside-out and can read what a customer needs. ' +
        "Lately the shop's been losing some traffic to online sellers and he's " +
        'looking for a steadier next move.',
    },
    payload: {
      country_code: 'GH',
      region: 'ashanti',
      education: 'I finished my WASSCE in 2020 in Kumasi.',
      experience:
        "Three years working at my uncle's electronics shop in Kumasi. " +
        'I help customers pick TVs, phones, fridges, and small appliances. ' +
        'I run the till, arrange deliveries, and sometimes do simple in-store repairs ' +
        'like replacing remote batteries or showing people how to use new devices.',
      skills_self_reported:
        'Customer service, persuasive selling, point of sale, cash handling, ' +
        'product knowledge across consumer electronics, basic stock counting, ' +
        'in-store troubleshooting and product demos.',
      additional_info:
        'I speak Twi natively, English fluently, and a little Hausa from northern customers.',
    },
  },
}

// Returns the matched persona or null. Accepts inputs like:
//   "Test: Amara"   "test: bern"   "TEST:Cal"   " test : amara "
export function matchTestCommand(input) {
  if (!input) return null
  const m = input.trim().match(/^test\s*:\s*(amara|bern|cal)\s*$/i)
  if (!m) return null
  return TEST_PERSONAS[m[1].toLowerCase()]
}

// Renders a persona's bio as a chat-friendly card-string.
export function formatPersonaBio(persona) {
  const b = persona.bio
  if (!b) return persona.label
  return (
    `${b.name}, ${b.age} — ${b.city}, ${b.country}\n` +
    `"${b.tagline}"\n\n` +
    `${b.headline}\n\n` +
    `${b.backstory}`
  )
}
