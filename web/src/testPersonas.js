// Canned profiles for "Test: <Name>" shortcut. Each persona is a fully
// pre-collected SkillsAssessmentRequest body — bypasses the chat back-and-forth
// and goes straight to /assess-skills + /match-opportunities.
//
// To add a persona: drop another entry here keyed by lowercase name.

export const TEST_PERSONAS = {
  amara: {
    label: 'Amara — Ghana, mobile phone repair (low-risk technical trade)',
    expectedVerdict: 'mostly_safe',
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
