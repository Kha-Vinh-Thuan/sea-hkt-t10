// Email the applicant (Odoo mail.compose.message): pick a template, edit the rendered subject / body, send.
// Given `stage` (after a stage move) it preselects that stage's template, and closes itself when the stage has none.
import { useEffect, useState } from 'react'
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField,
} from '@mui/material'
import { api, type MailTemplate, type Stage } from '../api'
import { t } from '../i18n'

type Props = {
  applicantId: number
  stage?: Stage
  onClose: () => void
  onSent: (notice: { sent: boolean; error: string | null }) => void
}

export default function ComposeEmailDialog({ applicantId, stage, onClose, onSent }: Props) {
  const [templates, setTemplates] = useState<MailTemplate[] | null>(null)
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function pick(id: number) {
    setTemplateId(id)
    try {
      const draft = await api.composeEmail(applicantId, id)
      setSubject(draft.subject)
      setBody(draft.body)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  useEffect(() => {
    api.mailTemplates().then((list) => {
      const forStage = stage && list.find((tpl) => tpl.stage === stage)
      if (stage && !forStage) return onClose() // nothing to offer for this stage
      setTemplates(list)
      if (forStage) pick(forStage.id)
    }).catch((e: Error) => { setTemplates([]); setError(e.message) })
    // Runs once per mount: the parent mounts a fresh dialog for every compose.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function send() {
    setBusy(true)
    setError('')
    try {
      onSent(await api.sendEmail(applicantId, { subject, body }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={templates !== null} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t('Send email')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select label={t('Template')} value={templateId} onChange={(e) => pick(Number(e.target.value))}>
            {(templates ?? []).map((tpl) => <MenuItem key={tpl.id} value={tpl.id}>{tpl.name}</MenuItem>)}
          </TextField>
          <TextField label={t('Subject')} value={subject} onChange={(e) => setSubject(e.target.value)} required />
          <TextField label={t('Body')} value={body} onChange={(e) => setBody(e.target.value)} multiline minRows={8} required />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('Cancel')}</Button>
        <Button variant="contained" onClick={send} loading={busy} disabled={!subject.trim() || !body.trim()}>{t('Send')}</Button>
      </DialogActions>
    </Dialog>
  )
}
