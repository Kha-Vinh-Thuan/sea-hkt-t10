// Vietnamese dictionary, split per area so files stay short; a key missing here falls back to English.
import board from './locales/vi.board'
import common from './locales/vi.common'
import interviews from './locales/vi.interviews'
import publicPages from './locales/vi.public'

export const vi: Record<string, string> = { ...common, ...board, ...interviews, ...publicPages }
