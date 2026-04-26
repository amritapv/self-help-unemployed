// i18n catalog for UNMAPPED. Lightweight, in-repo translations — no library.
// Adding a new language: append to LANGUAGES and add a key block in STRINGS.
// `t(lang, key)` falls back to English when a key is missing in the target language.

export const LANGUAGES = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'हिन्दी', native: 'हिन्दी (Hindi)' },
  { code: 'es', label: 'Español', native: 'Español (Spanish)' },
  { code: 'ar', label: 'العربية', native: 'العربية (Arabic)' },
  { code: 'fr', label: 'Français', native: 'Français (French)' },
]

// NOTE: The literal command tokens 'Test: Amara', 'Test: Bern', 'Test: Cal'
// MUST stay in Latin script across all languages — those are the exact strings
// the user has to type into the chat to trigger the test persona hotkey.

export const STRINGS = {
  en: {
    greeting:
      "Hi! I'm here to help you understand your skills and find opportunities. Let's start - what's your educational background? This could be formal schooling, certifications, or any training you've done.\n\n" +
      "Tip: type 'Test: Amara', 'Test: Bern', or 'Test: Cal' to skip the chat and run a simulated assessment with a pre-built persona.",
    inputPlaceholder: "Type your message... or 'Test: Amara' / 'Test: Bern' / 'Test: Cal'",
    sendButton: 'Send',
    analyzingMessage: 'Analyzing your skills and finding opportunities...',
    loadingPersona: 'Loading test persona: {label}',
    readyToAnalyze: 'Ready to analyze your skills!',
    generateProfileButton: 'Generate My Skills Profile',
    connectionError: "Sorry, I'm having trouble connecting. Please try again.",
    assessmentError: "Sorry, I couldn't complete the assessment. Please try again.",
    noMatchFallback: "I couldn't find a good match — try giving me a bit more detail about your skills.",
    topNOpportunities: 'Here are your top {n} opportunities:',
    basedOnInput: 'Based on what you told me:\n\n{summary}\n\nHere are your top {n} opportunities:',
    whyItFits: 'Why it fits',
    wage: 'Wage',
    outlook: 'Outlook',
    gap: 'Gap',
    nextStep: 'Next step',
    headerTitle: 'UNMAPPED',
    countryLabel: 'Country',
    languageLabel: 'Language',
    confirmLanguageSwitch: 'Switching language will reset the chat. Continue?',
    automationOutlook: 'Automation outlook',
    machinesGettingBetter: "What machines are getting better at",
    stillNeedsYou: "What still needs you",
    worthPickingUp: 'Worth picking up',
  },

  hi: {
    // Hindi (Devanagari). Tone: friendly, second-person informal ("आप" — polite-default,
    // since the audience is unknown youth and Hindi defaults to polite forms in UI).
    greeting:
      "नमस्ते! मैं आपके कौशल को समझने और अवसर खोजने में आपकी मदद के लिए यहाँ हूँ। चलिए शुरू करते हैं — आपकी शैक्षिक पृष्ठभूमि क्या है? यह औपचारिक पढ़ाई, प्रमाणपत्र, या कोई भी प्रशिक्षण हो सकता है जो आपने लिया हो।\n\n" +
      "सुझाव: चैट छोड़कर पहले से बनी प्रोफ़ाइल पर सिमुलेटेड मूल्यांकन चलाने के लिए 'Test: Amara', 'Test: Bern', या 'Test: Cal' टाइप करें।",
    inputPlaceholder: "अपना संदेश लिखें... या 'Test: Amara' / 'Test: Bern' / 'Test: Cal'",
    sendButton: 'भेजें',
    analyzingMessage: 'आपके कौशल का विश्लेषण कर रहे हैं और अवसर ढूँढ रहे हैं...',
    loadingPersona: 'टेस्ट प्रोफ़ाइल लोड हो रही है: {label}',
    readyToAnalyze: 'आपके कौशल का विश्लेषण करने के लिए तैयार!',
    generateProfileButton: 'मेरी कौशल प्रोफ़ाइल बनाएँ',
    connectionError: 'क्षमा करें, कनेक्ट करने में समस्या हो रही है। कृपया दोबारा प्रयास करें।',
    assessmentError: 'क्षमा करें, मूल्यांकन पूरा नहीं हो सका। कृपया दोबारा प्रयास करें।',
    noMatchFallback: 'मुझे कोई अच्छा मेल नहीं मिला — कृपया अपने कौशल के बारे में थोड़ा और बताएँ।',
    topNOpportunities: 'ये रहे आपके लिए शीर्ष {n} अवसर:',
    basedOnInput: 'आपने जो बताया, उसके आधार पर:\n\n{summary}\n\nये रहे आपके लिए शीर्ष {n} अवसर:',
    whyItFits: 'क्यों उपयुक्त है',
    wage: 'वेतन',
    outlook: 'भविष्य',
    gap: 'कमी',
    nextStep: 'अगला कदम',
    headerTitle: 'UNMAPPED',
    countryLabel: 'देश',
    languageLabel: 'भाषा',
    confirmLanguageSwitch: 'भाषा बदलने पर चैट रीसेट हो जाएगी। क्या जारी रखना है?',
    automationOutlook: 'ऑटोमेशन का असर',
    machinesGettingBetter: 'मशीनें किसमें बेहतर हो रही हैं',
    stillNeedsYou: 'किसमें अभी भी आपकी ज़रूरत है',
    worthPickingUp: 'सीखने लायक',
  },

  es: {
    // Spanish, neutral Latin American register (the audience is LMIC youth; "tú" feels
    // friendlier than "usted" for a peer-style assistant).
    greeting:
      "¡Hola! Estoy aquí para ayudarte a entender tus habilidades y encontrar oportunidades. Empecemos: ¿cuál es tu formación académica? Puede ser educación formal, certificaciones o cualquier capacitación que hayas hecho.\n\n" +
      "Tip: escribe 'Test: Amara', 'Test: Bern' o 'Test: Cal' para saltar el chat y ver una evaluación simulada con un perfil predefinido.",
    inputPlaceholder: "Escribe tu mensaje... o 'Test: Amara' / 'Test: Bern' / 'Test: Cal'",
    sendButton: 'Enviar',
    analyzingMessage: 'Analizando tus habilidades y buscando oportunidades...',
    loadingPersona: 'Cargando perfil de prueba: {label}',
    readyToAnalyze: '¡Listo para analizar tus habilidades!',
    generateProfileButton: 'Generar mi perfil de habilidades',
    connectionError: 'Lo siento, tengo problemas para conectarme. Inténtalo de nuevo.',
    assessmentError: 'Lo siento, no pude completar la evaluación. Inténtalo de nuevo.',
    noMatchFallback: 'No encontré una buena coincidencia — intenta darme un poco más de detalle sobre tus habilidades.',
    topNOpportunities: 'Estas son tus {n} mejores oportunidades:',
    basedOnInput: 'Según lo que me contaste:\n\n{summary}\n\nEstas son tus {n} mejores oportunidades:',
    whyItFits: 'Por qué encaja',
    wage: 'Salario',
    outlook: 'Perspectiva',
    gap: 'Brecha',
    nextStep: 'Próximo paso',
    headerTitle: 'UNMAPPED',
    countryLabel: 'País',
    languageLabel: 'Idioma',
    confirmLanguageSwitch: 'Cambiar el idioma reiniciará el chat. ¿Continuar?',
    automationOutlook: 'Perspectiva de automatización',
    machinesGettingBetter: 'En qué están mejorando las máquinas',
    stillNeedsYou: 'Qué todavía te necesita',
    worthPickingUp: 'Vale la pena aprender',
  },

  ar: {
    // Arabic (Modern Standard Arabic). Friendly tone, second-person masculine default
    // (which is the conventional unmarked form in MSA UI copy). Test command tokens
    // stay in Latin since the user must type them exactly.
    greeting:
      "مرحبًا! أنا هنا لمساعدتك على فهم مهاراتك والعثور على فرص. لنبدأ — ما هي خلفيتك التعليمية؟ يمكن أن تكون دراسة رسمية أو شهادات أو أي تدريب أجريته.\n\n" +
      "تلميح: اكتب 'Test: Amara' أو 'Test: Bern' أو 'Test: Cal' لتخطي المحادثة وتشغيل تقييم تجريبي بملف شخصي جاهز.",
    inputPlaceholder: "اكتب رسالتك... أو 'Test: Amara' / 'Test: Bern' / 'Test: Cal'",
    sendButton: 'إرسال',
    analyzingMessage: 'نحلّل مهاراتك ونبحث عن الفرص...',
    loadingPersona: 'جارٍ تحميل الملف التجريبي: {label}',
    readyToAnalyze: 'جاهز لتحليل مهاراتك!',
    generateProfileButton: 'أنشئ ملف مهاراتي',
    connectionError: 'عذرًا، لدي مشكلة في الاتصال. يُرجى المحاولة مرة أخرى.',
    assessmentError: 'عذرًا، لم أتمكن من إكمال التقييم. يُرجى المحاولة مرة أخرى.',
    noMatchFallback: 'لم أجد تطابقًا جيدًا — حاول إعطائي مزيدًا من التفاصيل عن مهاراتك.',
    topNOpportunities: 'إليك أفضل {n} فرص لك:',
    basedOnInput: 'بناءً على ما أخبرتني به:\n\n{summary}\n\nإليك أفضل {n} فرص لك:',
    whyItFits: 'لماذا تناسبك',
    wage: 'الأجر',
    outlook: 'الآفاق',
    gap: 'الفجوة',
    nextStep: 'الخطوة التالية',
    headerTitle: 'UNMAPPED',
    countryLabel: 'البلد',
    languageLabel: 'اللغة',
    confirmLanguageSwitch: 'سيؤدي تغيير اللغة إلى إعادة ضبط المحادثة. هل تريد المتابعة؟',
    automationOutlook: 'توقعات الأتمتة',
    machinesGettingBetter: 'ما الذي تتحسن فيه الآلات',
    stillNeedsYou: 'ما يزال يحتاج إليك',
    worthPickingUp: 'يستحق التعلم',
  },

  fr: {
    // French, second-person informal "tu" (matches the peer-coach tone of the English source;
    // a more formal product might prefer "vous", but the English greeting is clearly informal).
    greeting:
      "Salut ! Je suis là pour t'aider à comprendre tes compétences et trouver des opportunités. Commençons — quel est ton parcours scolaire ? Cela peut être une scolarité classique, des certifications ou toute formation que tu as suivie.\n\n" +
      "Astuce : tape 'Test: Amara', 'Test: Bern' ou 'Test: Cal' pour sauter le chat et lancer une évaluation simulée avec un profil pré-rempli.",
    inputPlaceholder: "Écris ton message... ou 'Test: Amara' / 'Test: Bern' / 'Test: Cal'",
    sendButton: 'Envoyer',
    analyzingMessage: 'Analyse de tes compétences et recherche d\'opportunités...',
    loadingPersona: 'Chargement du profil de test : {label}',
    readyToAnalyze: 'Prêt à analyser tes compétences !',
    generateProfileButton: 'Générer mon profil de compétences',
    connectionError: 'Désolé, je n\'arrive pas à me connecter. Réessaie, s\'il te plaît.',
    assessmentError: 'Désolé, je n\'ai pas pu terminer l\'évaluation. Réessaie, s\'il te plaît.',
    noMatchFallback: 'Je n\'ai pas trouvé de bonne correspondance — essaie de me donner un peu plus de détails sur tes compétences.',
    topNOpportunities: 'Voici tes {n} meilleures opportunités :',
    basedOnInput: 'D\'après ce que tu m\'as dit :\n\n{summary}\n\nVoici tes {n} meilleures opportunités :',
    whyItFits: 'Pourquoi ça te convient',
    wage: 'Salaire',
    outlook: 'Perspectives',
    gap: 'Écart',
    nextStep: 'Prochaine étape',
    headerTitle: 'UNMAPPED',
    countryLabel: 'Pays',
    languageLabel: 'Langue',
    confirmLanguageSwitch: 'Changer de langue réinitialisera le chat. Continuer ?',
    automationOutlook: "Perspectives d'automatisation",
    machinesGettingBetter: 'Ce que les machines font mieux',
    stillNeedsYou: 'Ce qui a encore besoin de vous',
    worthPickingUp: 'À apprendre',
  },
}

/**
 * Look up a translation. Falls back to English if the key is missing in `lang`,
 * and finally to the key itself if neither has it (so you see the missing key
 * in the UI rather than `undefined`).
 */
export function t(lang, key) {
  const langStrings = STRINGS[lang] || STRINGS.en
  if (langStrings && key in langStrings) return langStrings[key]
  if (STRINGS.en && key in STRINGS.en) return STRINGS.en[key]
  return key
}

export function isRTL(lang) {
  return lang === 'ar'
}
