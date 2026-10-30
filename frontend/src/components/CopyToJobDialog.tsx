// "Copy to job" from the applicant drawer (Odoo action_job_add_applicants): same person and CV, new application in `new`.
import { useEffect, useState } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField } from '@mui/material'
import { api, type Applicant, type Job } from '../api'
import { t } from '../i18n'

type Props = { applicant: Applicant; open: boolean; onClose: () => void; onCopied: (copy: Applicant, jobTitle: string) => void }

export default function CopyToJobDialog({ applicant, open, onClose, onCopied }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [jobId, setJobId] = useState<number | ''>('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setJobId('')
    setError('')
    api.jobs().then(setJobs).catch((e: Error) => setError(e.message))
  }, [open])

  async function copy() {
    if (jobId === '') return
    setBusy(true)
    try {
      onCopied(await api.copyApplicant(applicant.id, jobId), jobs.find((j) => j.id === jobId)?.title ?? '')
    } catch (e) {
      setError((e as Error).message) // e.g. 409: this email already applied there
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{t('Copy {name} to another job', { name: applicant.name })}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <TextField select fullWidth label={t('Job')} value={jobId} sx={{ mt: 1 }}
          onChange={(e) => setJobId(Number(e.target.value))}>
          {jobs.filter((j) => j.id !== applicant.job_id).map((j) => (
            <MenuItem key={j.id} value={j.id}>{j.title}{j.is_open ? '' : ` (${t('closed')})`}</MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('Cancel')}</Button>
        <Button variant="contained" onClick={copy} loading={busy} disabled={jobId === ''}>{t('Copy')}</Button>
      </DialogActions>
    </Dialog>
  )
}
