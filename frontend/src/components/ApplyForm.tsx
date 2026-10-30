// Apply form for one job: name, email, phone, LinkedIn, short introduction, CV file. The server re-validates everything.
import { useState, type FormEvent } from 'react'
import { Alert, Button, Stack, TextField, Typography } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { api } from '../api'

const MAX_MB = 5

export default function ApplyForm({ jobId }: { jobId: number }) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return setError('Please attach your CV.')
    if (file.size > MAX_MB * 1024 * 1024) return setError(`CV must be ${MAX_MB} MB or smaller.`)
    const form = new FormData(event.currentTarget)
    form.set('cv', file)
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

  if (done) return <Alert severity="success">Thanks! Your application was received. We will contact you by email.</Alert>

  return (
    <Stack component="form" spacing={2} onSubmit={submit} noValidate={false}>
      <TextField name="name" label="Full name" required fullWidth autoComplete="name" />
      <TextField name="email" label="Email" type="email" required fullWidth autoComplete="email" />
      <TextField name="phone" label="Phone" fullWidth autoComplete="tel" />
      <TextField name="linkedin" label="LinkedIn profile" type="url" fullWidth placeholder="https://www.linkedin.com/in/…" />
      <TextField name="short_intro" label="Short introduction" fullWidth multiline minRows={3}
        slotProps={{ htmlInput: { maxLength: 2000 } }} />
      <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
        {file ? 'Change CV' : 'Upload CV'}
        <input hidden type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </Button>
      <Typography variant="caption" color="text.secondary">
        {file ? file.name : `PDF, DOCX or TXT, up to ${MAX_MB} MB`}
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Button type="submit" variant="contained" size="large" disabled={busy}>
        {busy ? 'Submitting…' : 'Submit application'}
      </Button>
    </Stack>
  )
}
