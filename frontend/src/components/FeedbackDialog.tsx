// Scorecard after an interview: done (score required) or no-show, recommendation and notes.
import { useState, type FormEvent } from 'react'
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Rating, Stack, TextField, Typography,
} from '@mui/material'
import { api, RECOMMENDATION_LABEL, type FeedbackInput, type Interview, type Recommendation } from '../api'

type Props = { interview: Interview; open: boolean; onClose: () => void; onSaved: () => void }

export default function FeedbackDialog({ interview, open, onClose, onSaved }: Props) {
  const [status, setStatus] = useState<FeedbackInput['status']>(interview.status === 'no_show' ? 'no_show' : 'done')
  const [score, setScore] = useState<number | null>(interview.score)
  const [recommendation, setRecommendation] = useState<Recommendation | ''>(interview.recommendation ?? '')
  const [feedback, setFeedback] = useState(interview.feedback)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const done = status === 'done'
      await api.interviewFeedback(interview.id, {
        status, score: done ? score : null, recommendation: done && recommendation ? recommendation : null, feedback,
      })
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={submit}>
        <DialogTitle>Interview feedback</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField select label="Outcome" value={status}
              onChange={(e) => setStatus(e.target.value as FeedbackInput['status'])}>
              <MenuItem value="done">Done</MenuItem>
              <MenuItem value="no_show">No-show</MenuItem>
            </TextField>
            {status === 'done' && (
              <>
                <Stack>
                  <Typography variant="caption" color="text.secondary" component="label" id="score-label">Score *</Typography>
                  <Rating value={score} onChange={(_e, value) => setScore(value)} aria-labelledby="score-label" />
                </Stack>
                <TextField select label="Recommendation" value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value as Recommendation | '')}>
                  <MenuItem value="">—</MenuItem>
                  {Object.entries(RECOMMENDATION_LABEL).map(([value, label]) => (
                    <MenuItem key={value} value={value}>{label}</MenuItem>
                  ))}
                </TextField>
              </>
            )}
            <TextField label="Notes" multiline minRows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy || (status === 'done' && !score)}>Save</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
