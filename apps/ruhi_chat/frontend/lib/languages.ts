// The 10 target Indian languages plus auto-detect.
// ISO codes match shared/config.py supported_languages; labels show native
// script next to the English name so the switcher reads well in any script.
export type LangCode =
  | "auto"
  | "en"
  | "te"
  | "hi"
  | "ta"
  | "kn"
  | "ml"
  | "bn"
  | "mr"
  | "gu"
  | "pa"
  | "or";

export const LANGUAGES: { code: LangCode; label: string; native: string }[] = [
  { code: "auto", label: "Auto", native: "🌐 Auto-detect" },
  { code: "en", label: "English", native: "English" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", label: "Malayalam", native: "മലയാളം" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "mr", label: "Marathi", native: "मराठी" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી" },
  { code: "pa", label: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "or", label: "Odia", native: "ଓଡ଼ିଆ" },
];

export type ScriptMode = "native" | "latin" | "devanagari";

export const SCRIPT_MODES: { id: ScriptMode; label: string }[] = [
  { id: "native", label: "Native" },
  { id: "latin", label: "Latin" },
  { id: "devanagari", label: "Devanagari" },
];
