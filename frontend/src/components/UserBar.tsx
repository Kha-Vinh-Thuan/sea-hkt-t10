// Thin strip above every staff screen: who is signed in, admin's switch to the Users / Email templates pages,
// Google Calendar connect / disconnect, sign out. Kept outside BoardPage so the board's own header stays untouched.
import { Button, Chip, Stack, Typography } from '@mui/material'
import EventIcon from '@mui/icons-material/Event'
import LogoutIcon from '@mui/icons-material/Logout'
import { api, ROLE_LABEL, type UserBrief } from '../api'

export type StaffPage = 'board' | 'users' | 'templates'
const ADMIN_PAGES: [StaffPage, string][] = [['board', 'Recruitment'], ['users', 'Users'], ['templates', 'Email templates']]

type Props = {
  user: UserBrief & { google_connected?: boolean }
  page: StaffPage
  onPage: (page: StaffPage) => void
  onSignOut: () => void
  onGoogleChanged: () => void
  onError: (e: Error) => void
}

export default function UserBar({ user, page, onPage, onSignOut, onGoogleChanged, onError }: Props) {
  // Full-page redirect to Google's consent screen; Google sends the browser back to /?google=connected.
  function connect() {
    api.googleConnectUrl().then(({ url }) => { window.location.href = url }).catch(onError)
  }

  function disconnect() {
    if (!window.confirm('Disconnect Google Calendar? New interviews will no longer be added to it.')) return
    api.googleDisconnect().then(onGoogleChanged).catch(onError)
  }

  return (
    <Stack direction="row" spacing={1} sx={{ px: 2, py: 0.5, alignItems: 'center', justifyContent: 'flex-end',
      bgcolor: 'action.hover', borderBottom: 1, borderColor: 'divider', flexWrap: 'wrap' }}>
      {user.role === 'admin' && ADMIN_PAGES.filter(([p]) => p !== page).map(([p, label]) => (
        <Button key={p} size="small" onClick={() => onPage(p)}>{label}</Button>
      ))}
      {user.google_connected
        ? <Button size="small" startIcon={<EventIcon />} onClick={disconnect}>Disconnect Google Calendar</Button>
        : <Button size="small" startIcon={<EventIcon />} onClick={connect}>Connect Google Calendar</Button>}
      <Typography variant="body2" fontWeight={600}>{user.name || user.email}</Typography>
      <Chip size="small" label={ROLE_LABEL[user.role]} />
      <Button size="small" startIcon={<LogoutIcon />} onClick={onSignOut}>Sign out</Button>
    </Stack>
  )
}
