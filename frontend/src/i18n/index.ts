import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";

// Internationalization setup. English is the only bundled locale. Translation
// keys follow the MODULE.FEATURE.ELEMENT convention (three or more segments).
i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false, // React already escapes values
  },
});

export default i18n;
