// i18n catalog for UNMAPPED. Lightweight, in-repo translations — no library.
// Adding a new language: append to LANGUAGES and add a key block in STRINGS.
// `t(lang, key)` falls back to English when a key is missing in the target language.

// Top-20 languages by total speakers. The first 5 ship with full UI
// translations in STRINGS below; the others fall back to English UI
// strings via t(). Sonnet still responds in the user's language for
// dynamic content (greeting reply, opportunities, risk summary).
export const LANGUAGES = [
  { code: 'en', label: 'English',     native: 'English',                    rtl: false },
  { code: 'zh', label: '中文',         native: '中文 (Mandarin)',             rtl: false },
  { code: 'hi', label: 'हिन्दी',        native: 'हिन्दी (Hindi)',              rtl: false },
  { code: 'es', label: 'Español',     native: 'Español (Spanish)',          rtl: false },
  { code: 'fr', label: 'Français',    native: 'Français (French)',          rtl: false },
  { code: 'ar', label: 'العربية',      native: 'العربية (Arabic)',            rtl: true  },
  { code: 'bn', label: 'বাংলা',       native: 'বাংলা (Bengali)',             rtl: false },
  { code: 'pt', label: 'Português',   native: 'Português (Portuguese)',     rtl: false },
  { code: 'ru', label: 'Русский',     native: 'Русский (Russian)',          rtl: false },
  { code: 'ur', label: 'اردو',        native: 'اردو (Urdu)',                rtl: true  },
  { code: 'id', label: 'Indonesian',  native: 'Bahasa Indonesia',           rtl: false },
  { code: 'de', label: 'Deutsch',     native: 'Deutsch (German)',           rtl: false },
  { code: 'ja', label: '日本語',       native: '日本語 (Japanese)',           rtl: false },
  { code: 'sw', label: 'Kiswahili',   native: 'Kiswahili (Swahili)',        rtl: false },
  { code: 'mr', label: 'मराठी',       native: 'मराठी (Marathi)',            rtl: false },
  { code: 'te', label: 'తెలుగు',       native: 'తెలుగు (Telugu)',             rtl: false },
  { code: 'tr', label: 'Türkçe',      native: 'Türkçe (Turkish)',           rtl: false },
  { code: 'ta', label: 'தமிழ்',        native: 'தமிழ் (Tamil)',               rtl: false },
  { code: 'vi', label: 'Tiếng Việt',  native: 'Tiếng Việt (Vietnamese)',    rtl: false },
  { code: 'ko', label: '한국어',       native: '한국어 (Korean)',             rtl: false },
]

export const STRINGS = {
  en: {
    greeting:
      "Hi! I'm here to help you understand your skills and find opportunities. Let's start - what's your educational background? This could be formal schooling, certifications, or any training you've done.",
    inputPlaceholder: 'Type your message...',
    sendButton: 'Send',
    analyzingMessage: 'Analyzing your skills and finding opportunities...',
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
      "नमस्ते! मैं आपके कौशल को समझने और अवसर खोजने में आपकी मदद के लिए यहाँ हूँ। चलिए शुरू करते हैं — आपकी शैक्षिक पृष्ठभूमि क्या है? यह औपचारिक पढ़ाई, प्रमाणपत्र, या कोई भी प्रशिक्षण हो सकता है जो आपने लिया हो।",
    inputPlaceholder: 'अपना संदेश लिखें...',
    sendButton: 'भेजें',
    analyzingMessage: 'आपके कौशल का विश्लेषण कर रहे हैं और अवसर ढूँढ रहे हैं...',
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
      "¡Hola! Estoy aquí para ayudarte a entender tus habilidades y encontrar oportunidades. Empecemos: ¿cuál es tu formación académica? Puede ser educación formal, certificaciones o cualquier capacitación que hayas hecho.",
    inputPlaceholder: 'Escribe tu mensaje...',
    sendButton: 'Enviar',
    analyzingMessage: 'Analizando tus habilidades y buscando oportunidades...',
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
    // (which is the conventional unmarked form in MSA UI copy).
    greeting:
      "مرحبًا! أنا هنا لمساعدتك على فهم مهاراتك والعثور على فرص. لنبدأ — ما هي خلفيتك التعليمية؟ يمكن أن تكون دراسة رسمية أو شهادات أو أي تدريب أجريته.",
    inputPlaceholder: 'اكتب رسالتك...',
    sendButton: 'إرسال',
    analyzingMessage: 'نحلّل مهاراتك ونبحث عن الفرص...',
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
      "Salut ! Je suis là pour t'aider à comprendre tes compétences et trouver des opportunités. Commençons — quel est ton parcours scolaire ? Cela peut être une scolarité classique, des certifications ou toute formation que tu as suivie.",
    inputPlaceholder: 'Écris ton message...',
    sendButton: 'Envoyer',
    analyzingMessage: 'Analyse de tes compétences et recherche d\'opportunités...',
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
  // Data-driven so adding another RTL language is just an entry in LANGUAGES.
  const entry = LANGUAGES.find((l) => l.code === lang)
  return !!entry?.rtl
}
