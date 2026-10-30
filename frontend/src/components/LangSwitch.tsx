// EN / VI toggle for the public screens and the login card, which have no navbar (same button as in NavBar).
import { Button, Tooltip } from '@mui/material'
import { setLang, useLang } from '../i18n'

export default function LangSwitch({ color }: { color?: 'inherit' | 'primary' }) {
  const lang = useLang()
  const label = lang === 'vi' ? 'Switch to English' : 'Chuyển sang tiếng Việt'
  return (
    <Tooltip title={label}>
      <Button size="small" color={color} onClick={() => setLang(lang === 'vi' ? 'en' : 'vi')} aria-label={label}
        sx={{ minWidth: 0, fontWeight: 700 }}>
        {lang === 'vi' ? 'VI' : 'EN'}
      </Button>
    </Tooltip>
  )
}
