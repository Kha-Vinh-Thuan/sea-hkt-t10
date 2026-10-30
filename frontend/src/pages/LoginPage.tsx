// Staff sign-in (admin, recruiter, interviewer). On success the token + user are stored and App picks the screen.
import { useState, type FormEvent } from 'react'
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline'
import { api, session, type UserBrief } from '../api'

export default function LoginPage({ onLoggedIn }: { onLoggedIn: (user: UserBrief) => void }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      const { token, user } = await api.login(String(form.get('email')), String(form.get('password')))
      session.save(token, user)
      onLoggedIn(user)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: 'background.default', p: 2 }}>
      <Card variant="outlined" sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack component="form" spacing={2.5} onSubmit={submit}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <WorkOutlineIcon color="primary" />
              <Typography variant="h5" fontWeight={800}>Sign in</Typography>
            </Stack>
            <TextField name="email" label="Email" type="email" required autoFocus autoComplete="username" />
            <TextField name="password" label="Password" type="password" required autoComplete="current-password" />
            {error && <Alert severity="error">{error}</Alert>}
            <Button type="submit" variant="contained" size="large" disabled={busy}>Sign in</Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}
