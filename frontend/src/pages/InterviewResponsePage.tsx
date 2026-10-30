// Public page from the invitation email's Accept / Decline links (/interview/:token?answer=accept|decline, no login).
// The answer is only recorded on a button click, not on load: mail scanners open links and must not answer for the candidate.
import { useEffect, useState } from 'react'
import { Alert, Box, Button, CircularProgress, Container, Link, Paper, Stack, Typography } from '@mui/material'
import { api, formatWhen, type CandidateInterview } from '../api'
import LangSwitch from '../components/LangSwitch'
import { t } from '../i18n'

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
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}><LangSwitch /></Box>
      <Paper sx={{ p: 3 }}>
        {interview ? (
          <Stack spacing={2}>
            <Typography variant="h5">{t('Interview for {job}', { job: interview.job_title })}</Typography>
            <Typography>
              {t('Hello {name}, your interview is on {when}.', {
                name: interview.candidate_name,
                when: formatWhen(interview.start) + (interview.location ? ` (${interview.location})` : ''),
              })}
            </Typography>
            {interview.meet_url && <Link href={interview.meet_url} target="_blank" rel="noreferrer">{t('Join with Google Meet')}</Link>}
            {interview.status === 'cancelled' && <Alert severity="info">{t('This interview has been cancelled.')}</Alert>}
            {interview.candidate_response !== 'none' && (
              <Alert severity={interview.candidate_response === 'accepted' ? 'success' : 'info'}>
                {interview.candidate_response === 'accepted' ? t('Your answer: accepted. Thank you!') : t('Your answer: declined. Thank you!')}
              </Alert>
            )}
            {error && <Alert severity="error">{error}</Alert>}
            {open && (
              <Stack direction="row" spacing={1}>
                <Button variant={suggested === 'accepted' ? 'contained' : 'outlined'} color="success" disabled={busy}
                  onClick={() => answer('accepted')}>{t('I will attend')}</Button>
                <Button variant={suggested === 'declined' ? 'contained' : 'outlined'} color="error" disabled={busy}
                  onClick={() => answer('declined')}>{t('I cannot attend')}</Button>
              </Stack>
            )}
          </Stack>
        ) : error ? <Alert severity="error">{error}</Alert> : <CircularProgress />}
      </Paper>
    </Container>
  )
}
