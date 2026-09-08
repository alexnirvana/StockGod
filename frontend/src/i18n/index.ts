import i18next from 'i18next'
import { initReactI18next, useTranslation } from 'react-i18next'
import en from './en.json'

export type Locale = 'zh-CN' | 'en'
export const supportedLocales: Locale[] = ['zh-CN', 'en']
export function normalizeLocale(value: string | null | undefined): Locale {
  return value?.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
}
function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem('stockgod.locale')
    if (saved && supportedLocales.includes(saved as Locale)) return saved as Locale
  } catch { /* Storage may be unavailable. */ }
  return normalizeLocale(typeof navigator === 'undefined' ? 'zh-CN' : navigator.language)
}

export const i18n = i18next.createInstance()
void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, 'zh-CN': { translation: Object.fromEntries(Object.keys(en).map(key => [key, key])) } },
  lng: initialLocale(), fallbackLng: 'zh-CN', supportedLngs: supportedLocales,
  keySeparator: false, nsSeparator: false, returnEmptyString: true,
  interpolation: { escapeValue: false }, initAsync: false,
})
function applyDocument(locale: string) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
    document.title = locale === 'en' ? 'Stock God · Learn. Practice. Grow.' : '我是股神 · Stock God'
  }
  try { localStorage.setItem('stockgod.locale', locale) } catch { /* Preference still works in memory. */ }
}
i18n.on('languageChanged', applyDocument)
applyDocument(i18n.language)
export const t = (key: string, values?: Record<string, unknown>): string => String(i18n.t(key, values))
export function useLocale(): Locale { return useTranslation().i18n.language as Locale }
export async function setLocale(locale: Locale) { await i18n.changeLanguage(locale) }
