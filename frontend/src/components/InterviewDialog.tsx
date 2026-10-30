// Book an interview for one applicant. Length comes from the job; the server checks the time and clashes.
import { useState, type FormEvent } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material'
import { api } from '../api'

type Props = {
  applicantId: number
  open: boolean
  onClose: () => void
  onBooked: (notice: { emailed: boolean; mailError: string | null }) => void
}

export default function InterviewDialog({ applicantId, open, onClose, onBooked }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    setBusy(true)
    setError('')
    try {
      // datetime-local has no timezone; toISOString sends it as UTC so the server stores the right instant.
      const result = await api.scheduleInterview(applicantId, {
        start: new Date(text('start')).toISOString(),
        interviewer_name: text('interviewer_name'),
        interviewer_email: text('interviewer_email'),
        location: text('location'),
      })
      onBooked({ emailed: result.emailed, mailError: result.mail_error })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={submit}>
        <DialogTitle>Schedule interview</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="start" label="Start" type="datetime-local" required slotProps={{ inputLabel: { shrink: true } }} />
            <TextField name="interviewer_name" label="Interviewer name" />
            <TextField name="interviewer_email" label="Interviewer email" type="email" required />
            <TextField name="location" label="Meeting link or room" placeholder="https://meet.google.com/…" />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>Book and send invite</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
