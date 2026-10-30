// Public page from the invitation email's Accept / Decline links (/interview/:token?answer=accept|decline, no login).
// The answer is only recorded on a button click, not on load: mail scanners open links and must not answer for the candidate.
import { useEffect, useState } from 'react'
import { Alert, Button, CircularProgress, Container, Link, Paper, Stack, Typography } from '@mui/material'
import { api, CANDIDATE_RESPONSE_LABEL, formatWhen, type CandidateInterview } from '../api'

export default function InterviewResponsePage({ token }: { token: string }) {
  const suggested = new URLSearchParams(window.location.search).get('answer') === 'decline' ? 'declined' : 'accepted'
  const [interview, setInterview] = useState<CandidateInterview | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.candidateInterview(token).then(setInterview).catch((e: Error) => setError(e.message)) }, [token])

  async function answer(value: 'accepted' | 'declined') {
    setBusy(true)
    setError('')
    try {
      setInterview(await api.answerInterview(token, value))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const open = interview?.status === 'scheduled' && new Date(interview.end).getTime() > Date.now()

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Paper sx={{ p: 3 }}>
        {interview ? (
          <Stack spacing={2}>
            <Typography variant="h5">Interview for {interview.job_title}</Typography>
            <Typography>
              Hello {interview.candidate_name}, your interview is on {formatWhen(interview.start)}
              {interview.location && ` (${interview.location})`}.
            </Typography>
            {interview.meet_url && <Link href={interview.meet_url} target="_blank" rel="noreferrer">Join with Google Meet</Link>}
            {interview.status === 'cancelled' && <Alert severity="info">This interview has been cancelled.</Alert>}
            {interview.candidate_response !== 'none' && (
              <Alert severity={interview.candidate_response === 'accepted' ? 'success' : 'info'}>
                Your answer: {CANDIDATE_RESPONSE_LABEL[interview.candidate_response].replace('Candidate ', '')}. Thank you!
              </Alert>
            )}
            {error && <Alert severity="error">{error}</Alert>}
            {open && (
              <Stack direction="row" spacing={1}>
                <Button variant={suggested === 'accepted' ? 'contained' : 'outlined'} color="success" disabled={busy}
                  onClick={() => answer('accepted')}>I will attend</Button>
                <Button variant={suggested === 'declined' ? 'contained' : 'outlined'} color="error" disabled={busy}
                  onClick={() => answer('declined')}>I cannot attend</Button>
              </Stack>
            )}
          </Stack>
        ) : error ? <Alert severity="error">{error}</Alert> : <CircularProgress />}
      </Paper>
    </Container>
  )
}
