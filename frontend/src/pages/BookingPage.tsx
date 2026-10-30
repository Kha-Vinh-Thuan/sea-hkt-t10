// Public page from the "pick a time" email (/book/:token, no login): the proposed times still free, one click books.
import { useEffect, useState } from 'react'
import { Alert, Box, Button, CircularProgress, Container, Paper, Stack, Typography } from '@mui/material'
import { api, formatWhen, type BookingPage as Booking } from '../api'
import LangSwitch from '../components/LangSwitch'
import { t } from '../i18n'

export default function BookingPage({ token }: { token: string }) {
  const [page, setPage] = useState<Booking | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [booked, setBooked] = useState<{ start: string; location: string } | null>(null)

  useEffect(() => { api.bookingPage(token).then(setPage).catch((e: Error) => setError(e.message)) }, [token])

  async function book(start: string) {
    if (!window.confirm(t('Book your interview on {when}?', { when: formatWhen(start) }))) return
    setBusy(true)
    setError('')
    try {
      setBooked(await api.bookSlot(token, start))
    } catch (e) {
      setError((e as Error).message)
      // Someone else may have taken it: reload the remaining times.
      api.bookingPage(token).then(setPage).catch(() => setPage(null))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}><LangSwitch /></Box>
      <Paper sx={{ p: 3 }}>
        {booked ? (
          <Alert severity="success">
            {t('Your interview is booked for {when}.', {
              when: formatWhen(booked.start) + (booked.location ? ` (${booked.location})` : ''),
            })}{' '}
            {t('A calendar invitation is on its way to your inbox.')}
          </Alert>
        ) : page ? (
          <Stack spacing={2}>
            <Typography variant="h5">{t('Interview for {job}', { job: page.job_title })}</Typography>
            <Typography>
              {t('Hello {name}, please pick a time that suits you ({minutes} minutes{location}).', {
                name: page.candidate_name, minutes: page.minutes, location: page.location ? `, ${page.location}` : '',
              })}
            </Typography>
            {error && <Alert severity="warning">{error}</Alert>}
            {page.slots.length === 0 ? (
              <Alert severity="info">{t('None of the proposed times is available any more. Please reply to the recruiter.')}</Alert>
            ) : (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {page.slots.map((s) => (
                  <Button key={s.start} variant="outlined" disabled={busy} onClick={() => book(s.start)}>
                    {formatWhen(s.start)}
                  </Button>
                ))}
              </Box>
            )}
            <Typography variant="caption" color="text.secondary">{t("Times are shown in your browser's time zone.")}</Typography>
          </Stack>
        ) : error ? <Alert severity="error">{error}</Alert> : <CircularProgress />}
      </Paper>
    </Container>
  )
}
