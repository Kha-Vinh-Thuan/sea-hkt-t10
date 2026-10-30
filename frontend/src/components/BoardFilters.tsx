// Board toolbar: search (name / email / CV / tags), minimum priority, exact tag, "mine" (I own) and archived switches.
import { useEffect, useState } from 'react'
import { FormControlLabel, InputAdornment, MenuItem, Stack, Switch, TextField } from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import type { ApplicantFilters } from '../api'
import { t } from '../i18n'

type Props = { value: ApplicantFilters; onChange: (filters: ApplicantFilters) => void }

const DEBOUNCE_MS = 300

export default function BoardFilters({ value, onChange }: Props) {
  // Text fields update locally and reach the parent after a pause, so typing doesn't fire one request per key.
  const [q, setQ] = useState(value.q ?? '')
  const [tag, setTag] = useState(value.tag ?? '')

  useEffect(() => {
    if (q === (value.q ?? '') && tag === (value.tag ?? '')) return
    const timer = setTimeout(() => onChange({ ...value, q, tag }), DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [q, tag, value, onChange])

  return (
    <Stack direction="row" spacing={1.5} sx={{ mb: 2, alignItems: 'center', flexWrap: 'wrap', rowGap: 1 }}>
      <TextField size="small" placeholder={t('Search name, email, CV, tags')} value={q} onChange={(e) => setQ(e.target.value)}
        slotProps={{
          input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> },
          htmlInput: { 'aria-label': t('Search applicants'), maxLength: 200 },
        }}
        sx={{ minWidth: 260 }} />
      <TextField select size="small" label={t('Min priority')} value={value.priority_min ?? ''} sx={{ minWidth: 130 }}
        onChange={(e) => onChange({ ...value, priority_min: e.target.value === '' ? undefined : Number(e.target.value) })}>
        <MenuItem value="">{t('Any')}</MenuItem>
        {[1, 2, 3].map((p) => <MenuItem key={p} value={p}>{'★'.repeat(p)}</MenuItem>)}
      </TextField>
      <TextField size="small" label={t('Tag')} value={tag} onChange={(e) => setTag(e.target.value)} sx={{ width: 140 }}
        slotProps={{ htmlInput: { maxLength: 100 } }} />
      <FormControlLabel label={t('Mine')}
        control={<Switch checked={value.owner === 'me'}
          onChange={(e) => onChange({ ...value, owner: e.target.checked ? 'me' : undefined })} />} />
      <FormControlLabel label={t('Show archived')}
        control={<Switch checked={!!value.archived} onChange={(e) => onChange({ ...value, archived: e.target.checked })} />} />
    </Stack>
  )
}
