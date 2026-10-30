// Tiny i18n without a library: the English text is the key, `vi` holds the Vietnamese; a missing entry falls back to
// English. Placeholders: t('Copied to {job}.', { job }). The root component calls useLang(), so switching language
// re-renders the whole tree. Texts coming from the API (errors, activity log, stage hints) stay as the server sends them.
import { useSyncExternalStore } from 'react'
import { vi } from './i18n.vi'

export type Lang = 'en' | 'vi'
const STORAGE_KEY = 'lang'

function initial(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'vi') return saved
  } catch { /* storage blocked: fall through */ }
  return navigator.language.toLowerCase().startsWith('vi') ? 'vi' : 'en'
}

let lang: Lang = initial()
document.documentElement.lang = lang
const listeners = new Set<() => void>()

export function setLang(next: Lang) {
  lang = next
  document.documentElement.lang = next
  try { localStorage.setItem(STORAGE_KEY, next) } catch { /* only this tab remembers */ }
  listeners.forEach((listener) => listener())
}

export function useLang(): Lang {
  return useSyncExternalStore((listener) => { listeners.add(listener); return () => { listeners.delete(listener) } }, () => lang)
}

export function t(text: string, values?: Record<string, string | number>): string {
  const out = lang === 'vi' ? vi[text] ?? text : text
  return values ? out.replace(/\{(\w+)\}/g, (match: string, key: string) => (key in values ? String(values[key]) : match)) : out
}

// For toLocaleString / toLocaleDateString, so dates follow the chosen language.
export const locale = () => (lang === 'vi' ? 'vi-VN' : 'en-US')
