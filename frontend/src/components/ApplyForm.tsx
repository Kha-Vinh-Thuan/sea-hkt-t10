// Apply form for one job: name, email, phone, LinkedIn, short introduction, CV file. The server re-validates everything.
import { useState, type FormEvent } from 'react'
import { Alert, Button, Stack, TextField, Typography } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { api, VISUALLY_HIDDEN } from '../api'
import { t } from '../i18n'

const MAX_MB = 5

export default function ApplyForm({ jobId }: { jobId: number }) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return setError(t('Please attach your CV.'))
    if (file.size > MAX_MB * 1024 * 1024) return setError(t('CV must be {mb} MB or smaller.', { mb: MAX_MB }))
    const form = new FormData(event.currentTarget)
    form.set('cv', file)
    // ?source=linkedin on the careers link says where the candidate came from; the server rejects unknown values.
    const source = new URLSearchParams(window.location.search).get('source')
    if (source) form.set('source', source)
    setBusy(true)
    setError('')
    try {
      await api.apply(jobId, form)
      setDone(true)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (done) return <Alert severity="success">{t('Thanks! Your application was received. We will contact you by email.')}</Alert>

  return (
    <Stack component="form" spacing={2} onSubmit={submit} noValidate={false}>
      <TextField name="name" label={t('Full name')} required fullWidth autoComplete="name" />
      <TextField name="email" label={t('Email')} type="email" required fullWidth autoComplete="email" />
      <TextField name="phone" label={t('Phone')} fullWidth autoComplete="tel" />
      <TextField name="linkedin" label={t('LinkedIn profile')} type="url" fullWidth placeholder="https://www.linkedin.com/in/…" />
      <TextField name="short_intro" label={t('Short introduction')} fullWidth multiline minRows={3}
        slotProps={{ htmlInput: { maxLength: 2000 } }} />
      <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
        {file ? t('Change CV') : t('Upload CV')}
        <input type="file" style={VISUALLY_HIDDEN} accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </Button>
      <Typography variant="caption" color="text.secondary">
        {file ? file.name : t('PDF, DOCX or TXT, up to {mb} MB', { mb: MAX_MB })}
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Button type="submit" variant="contained" size="large" loading={busy}>
        {busy ? t('Submitting…') : t('Submit application')}
      </Button>
    </Stack>
  )
}
