// Book an interview for one applicant, or reschedule one (pass `interview` to prefill). Length comes from the job;
// the server checks the time and clashes. The interviewer is picked from the job's list or typed in for outsiders.
// Step 1 picks how: "I pick the time" (week grid of every job interviewer's busy times, Google Calendar if connected;
// clicking a free cell fills interviewer + start) or "Let the candidate choose" (free-slot chips of one interviewer,
// several picked, emailed as a public page). Step 2 is the grid or chips, step 3 a one-line summary before sending.
import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, ToggleButton,
  ToggleButtonGroup, Typography,
} from '@mui/material'
import { api, formatWhen, type Interview, type Slot, type UserBrief } from '../api'
import { t } from '../i18n'
import TeamCalendar from './TeamCalendar'

type Props = {
  applicantId: number
  interview?: Interview
  open: boolean
  onClose: () => void
  onBooked: (notice: { emailed: boolean; mailError: string | null; proposed?: boolean }) => void
}

// datetime-local wants local 'YYYY-MM-DDTHH:mm' without a timezone.
function toLocalInput(iso: string) {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

const MAX_CHIPS = 40 // a week of half-hour steps is ~80; the first ones are what recruiters pick anyway

export default function InterviewDialog({ applicantId, interview, open, onClose, onBooked }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [choices, setChoices] = useState<UserBrief[]>([])
  const [name, setName] = useState(interview?.interviewer_name ?? '')
  const [email, setEmail] = useState(interview?.interviewer_email ?? '')
  const [start, setStart] = useState(interview ? toLocalInput(interview.start) : '')
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [propose, setPropose] = useState(false)
  const [chosen, setChosen] = useState<string[]>([])
  const [minutes, setMinutes] = useState(45)
  const [other, setOther] = useState(false) // interviewer typed in by hand (not in the job's list)

  // The job's interviewer list, or every active user when the job has none. Typed name/email = "Other".
  useEffect(() => {
    if (!open) return
    // The dialog stays mounted between openings, so start each one from the interview (or blank).
    setName(interview?.interviewer_name ?? '')
    setEmail(interview?.interviewer_email ?? '')
    setStart(interview ? toLocalInput(interview.start) : '')
    setPropose(false)
    setChosen([])
    setOther(false)
    Promise.all([api.applicant(applicantId), api.jobs(), api.users()])
      .then(([applicant, jobs, users]) => {
        const job = jobs.find((j) => j.id === applicant.job_id)
        const ids = job?.interviewer_ids ?? []
        const list = ids.length ? users.filter((u) => ids.includes(u.id)) : users
        setChoices(list)
        // Rescheduling an outsider: open the typed-in fields straight away.
        if (interview && !list.some((u) => u.email.toLowerCase() === interview.interviewer_email.toLowerCase())) setOther(true)
        if (job) setMinutes(job.interview_duration_minutes)
      })
      .catch((e: Error) => setError(e.message))
  }, [open, applicantId, interview])

  const picked = choices.find((u) => u.email.toLowerCase() === email.trim().toLowerCase())
  const pickedId = picked?.id
  useEffect(() => {
    setSlots(null)
    setChosen([])
    if (!open || pickedId === undefined || !propose) return
    api.freeSlots(pickedId, applicantId).then(setSlots).catch((e: Error) => setError(e.message))
  }, [open, pickedId, applicantId, propose])

  function pick(value: string) {
    const user = choices.find((u) => String(u.id) === value)
    setOther(!user)
    setName(user ? user.name : '')
    setEmail(user ? user.email : '')
  }

  function clickSlot(slot: Slot) {
    if (!propose) return setStart(toLocalInput(slot.start))
    setChosen((c) => (c.includes(slot.start) ? c.filter((s) => s !== slot.start) : [...c, slot.start]))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    setBusy(true)
    setError('')
    try {
      if (propose && pickedId !== undefined) {
        const result = await api.proposeSlots(applicantId, { interviewer_id: pickedId, slots: chosen, location: text('location') })
        onBooked({ emailed: result.emailed, mailError: result.mail_error, proposed: true })
        return
      }
      // datetime-local has no timezone; toISOString sends it as UTC so the server stores the right instant.
      const data = {
        start: new Date(start).toISOString(),
        interviewer_name: name.trim(),
        interviewer_email: email.trim(),
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
    <Dialog open={open} onClose={onClose} fullWidth maxWidth={propose ? 'sm' : 'md'}>
      <form onSubmit={submit}>
        <DialogTitle>{interview ? t('Reschedule interview') : t('Schedule interview')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {!interview && (
              <ToggleButtonGroup exclusive fullWidth color="primary" size="small" value={propose ? 'propose' : 'pick'}
                onChange={(_e, v) => { if (v) setPropose(v === 'propose') }}>
                <ToggleButton value="pick">{t('I pick the time')}</ToggleButton>
                <ToggleButton value="propose">{t('Let the candidate choose')}</ToggleButton>
              </ToggleButtonGroup>
            )}

            {!propose && choices.length > 0 && !other && (
              <TeamCalendar interviewers={choices} minutes={minutes}
                selected={picked && start ? { start: new Date(start).toISOString(), userId: picked.id } : undefined}
                onPick={(at, user) => { setName(user.name); setEmail(user.email); setStart(toLocalInput(at.toISOString())) }} />
            )}

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField label={t('Interviewer')} select fullWidth value={other ? 'other' : picked ? String(picked.id) : ''}
                onChange={(e) => pick(e.target.value)}>
                {choices.map((u) => <MenuItem key={u.id} value={String(u.id)}>{u.name || u.email} ({u.email})</MenuItem>)}
                <MenuItem value="other">{t('Someone else (type name and email)')}</MenuItem>
              </TextField>
              {!propose && (
                <TextField label={t('Start')} type="datetime-local" required fullWidth slotProps={{ inputLabel: { shrink: true } }}
                  value={start} onChange={(e) => setStart(e.target.value)} />
              )}
            </Stack>
            {other && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField label={t('Interviewer name')} fullWidth value={name} onChange={(e) => setName(e.target.value)} />
                <TextField label={t('Interviewer email')} type="email" required fullWidth value={email}
                  onChange={(e) => setEmail(e.target.value)} />
              </Stack>
            )}

            {propose && !picked && <Alert severity="info">{t('Choose an interviewer from the list to see their free times.')}</Alert>}
            {propose && picked && (
              <Box>
                <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
                  {t('Tick the times to offer; the candidate gets an email and picks one')}
                </Typography>
                {slots === null ? <Typography variant="body2">{t('Loading…')}</Typography>
                  : slots.length === 0 ? <Typography variant="body2">{t('No free time in the next 7 days.')}</Typography>
                  : (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxHeight: 160, overflowY: 'auto' }}>
                      {slots.slice(0, MAX_CHIPS).map((s) => {
                        const selected = chosen.includes(s.start)
                        return <Chip key={s.start} size="small" label={formatWhen(s.start)} onClick={() => clickSlot(s)}
                          color={selected ? 'success' : 'default'} variant={selected ? 'filled' : 'outlined'} />
                      })}
                    </Box>
                  )}
              </Box>
            )}

            <TextField name="location" label={t('Meeting link or room')}
              helperText={t('Leave empty to use a Google Meet link when the interviewer connected Google Calendar')}
              defaultValue={interview?.location} />
            {!propose && start && email && (
              <Alert severity="success" icon={false}>
                <b>{formatWhen(new Date(start).toISOString())}</b> · {t('{n} min', { n: minutes })} · {name || email}
              </Alert>
            )}
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t('Cancel')}</Button>
          {propose ? (
            <Button type="submit" variant="contained" loading={busy} disabled={chosen.length === 0}>
              {t(chosen.length === 1 ? 'Email {n} time to candidate' : 'Email {n} times to candidate', { n: chosen.length })}
            </Button>
          ) : (
            <Button type="submit" variant="contained" loading={busy}>
              {interview ? t('Update and send invite') : t('Book and send invite')}
            </Button>
          )}
        </DialogActions>
      </form>
    </Dialog>
  )
}
