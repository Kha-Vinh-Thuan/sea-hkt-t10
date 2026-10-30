// Book an interview for one applicant, or reschedule one (pass `interview` to prefill). Length comes from the job;
// the server checks the time and clashes. The interviewer is picked from the job's list or typed in for outsiders.
import { useEffect, useState, type FormEvent } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from '@mui/material'
import { api, type Interview, type UserBrief } from '../api'

type Props = {
  applicantId: number
  interview?: Interview
  open: boolean
  onClose: () => void
  onBooked: (notice: { emailed: boolean; mailError: string | null }) => void
}

// datetime-local wants local 'YYYY-MM-DDTHH:mm' without a timezone.
function toLocalInput(iso: string) {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

export default function InterviewDialog({ applicantId, interview, open, onClose, onBooked }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [choices, setChoices] = useState<UserBrief[]>([])
  const [name, setName] = useState(interview?.interviewer_name ?? '')
  const [email, setEmail] = useState(interview?.interviewer_email ?? '')

  // The job's interviewer list, or every active user when the job has none. Typed name/email = "Other".
  useEffect(() => {
    if (!open) return
    // The dialog stays mounted between openings, so start each one from the interview (or blank).
    setName(interview?.interviewer_name ?? '')
    setEmail(interview?.interviewer_email ?? '')
    Promise.all([api.applicant(applicantId), api.jobs(), api.users()])
      .then(([applicant, jobs, users]) => {
        const ids = jobs.find((j) => j.id === applicant.job_id)?.interviewer_ids ?? []
        setChoices(ids.length ? users.filter((u) => ids.includes(u.id)) : users)
      })
      .catch((e: Error) => setError(e.message))
  }, [open, applicantId, interview])

  const picked = choices.find((u) => u.email.toLowerCase() === email.trim().toLowerCase())
  function pick(value: string) {
    const user = choices.find((u) => String(u.id) === value)
    setName(user ? user.name : '')
    setEmail(user ? user.email : '')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    setBusy(true)
    setError('')
    try {
      // datetime-local has no timezone; toISOString sends it as UTC so the server stores the right instant.
      const data = {
        start: new Date(text('start')).toISOString(),
        interviewer_name: text('interviewer_name'),
        interviewer_email: text('interviewer_email'),
        location: text('location'),
      }
      const result = interview
        ? await api.rescheduleInterview(interview.id, data)
        : await api.scheduleInterview(applicantId, data)
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
        <DialogTitle>{interview ? 'Reschedule interview' : 'Schedule interview'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="start" label="Start" type="datetime-local" required slotProps={{ inputLabel: { shrink: true } }}
              defaultValue={interview && toLocalInput(interview.start)} />
            <TextField label="Interviewer" select value={picked ? String(picked.id) : 'other'}
              onChange={(e) => pick(e.target.value)}>
              {choices.map((u) => <MenuItem key={u.id} value={String(u.id)}>{u.name || u.email} ({u.email})</MenuItem>)}
              <MenuItem value="other">Other (type below)</MenuItem>
            </TextField>
            <TextField name="interviewer_name" label="Interviewer name" value={name} onChange={(e) => setName(e.target.value)} />
            <TextField name="interviewer_email" label="Interviewer email" type="email" required
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField name="location" label="Meeting link or room" placeholder="https://meet.google.com/…"
              defaultValue={interview?.location} />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>{interview ? 'Update and send invite' : 'Book and send invite'}</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
