// Picks the page from the URL and the signed-in role: /careers/*, /book/:token and /interview/:token are public
// (job board, candidate picks an interview time, candidate accepts / declines); staff need a login.
// Interviewers only get their interviews; admins also get the Users / Email templates pages; everyone else the board tabs.
// ponytail: plain links + pathname switch, no router; add react-router when pages need nested layouts.
import { useCallback, useEffect, useState } from 'react'
import { Alert, Box } from '@mui/material'
import { t, useLang } from './i18n'
import { api, session, UnauthorizedError, type Me, type UserBrief } from './api'
import NavBar, { type StaffPage } from './components/NavBar'
import BoardPage from './pages/BoardPage'
import BookingPage from './pages/BookingPage'
import CareersPage from './pages/CareersPage'
import InterviewResponsePage from './pages/InterviewResponsePage'
import InterviewsPage from './pages/InterviewsPage'
import LoginPage from './pages/LoginPage'
import MailTemplatesPage from './pages/MailTemplatesPage'
import UsersPage from './pages/UsersPage'

const GOOGLE_RESULT_TEXT: Record<string, string> = {
  connected: 'Google Calendar connected.',
  denied: 'Google Calendar was not connected (access denied).',
  error: 'Google Calendar could not be connected, please try again.',
}

function Screens() {
  const [user, setUser] = useState<UserBrief | Me | null>(() => (session.token() ? session.user() : null))
  const [page, setPage] = useState<StaffPage>('pipeline')
  // Google's consent screen sends the browser back to /?google=connected|denied|error.
  const [googleResult] = useState(() => new URLSearchParams(window.location.search).get('google'))
  useEffect(() => { if (googleResult) window.history.replaceState(null, '', '/') }, [googleResult])

  function signOut() {
    session.clear()
    setUser(null)
    setPage('pipeline')
  }

  // request() already cleared the stored session on a 401; just drop back to the login page.
  const onError = useCallback((e: Error) => { if (e instanceof UnauthorizedError) setUser(null) }, [])

  // The stored role may be stale (admin changed it); refresh it once per load (and after Google connect changes).
  const signedIn = user !== null
  const refreshMe = useCallback(() => {
    api.me().then((me) => { session.saveUser(me); setUser(me) }).catch(onError)
  }, [onError])
  useEffect(() => { if (signedIn) refreshMe() }, [signedIn, refreshMe])

  const path = window.location.pathname
  const booking = path.match(/^\/book\/([\w-]+)\/?$/)
  if (booking) return <BookingPage token={booking[1]} />
  const response = path.match(/^\/interview\/([\w-]+)\/?$/)
  if (response) return <InterviewResponsePage token={response[1]} />
  const match = path.match(/^\/careers(?:\/(\d+))?\/?$/)
  if (match) return <CareersPage jobId={match[1] ? Number(match[1]) : undefined} />
  if (!user) return <LoginPage onLoggedIn={setUser} />

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <NavBar user={user} page={page} onPage={setPage} onSignOut={signOut} onGoogleChanged={refreshMe}
        onError={(e) => { onError(e); window.alert(e.message) }} />
      {googleResult && GOOGLE_RESULT_TEXT[googleResult] && (
        <Alert severity={googleResult === 'connected' ? 'success' : 'warning'} sx={{ m: 1 }}>
          {t(GOOGLE_RESULT_TEXT[googleResult])}
        </Alert>
      )}
      {user.role === 'interviewer' ? (
        <Box sx={{ p: 2 }}><InterviewsPage onError={onError} /></Box>
      ) : user.role === 'admin' && page === 'users' ? (
        <Box sx={{ p: 2 }}><UsersPage currentUserId={user.id} onError={onError} /></Box>
      ) : user.role === 'admin' && page === 'templates' ? (
        <Box sx={{ p: 2 }}><MailTemplatesPage onError={onError} /></Box>
      ) : (
        <BoardPage tab={page === 'users' || page === 'templates' ? 'pipeline' : page} onTab={setPage} onSignedOut={signOut} />
      )}
    </Box>
  )
}

// Subscribing here re-renders the whole tree (nothing is memoised) when the language changes, keeping page state.
export default function App() {
  useLang()
  return <Screens />
}
