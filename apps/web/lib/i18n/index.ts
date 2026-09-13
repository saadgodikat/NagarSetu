import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import mr from './mr.json'

i18next.use(initReactI18next).init({
  lng: typeof window !== 'undefined' ? (localStorage.getItem('smcp_lang') ?? 'en') : 'en',
  fallbackLng: 'en',
  resources: {
    en: { translation: en },
    mr: { translation: mr },
  },
  interpolation: { escapeValue: false },
})

export default i18next
