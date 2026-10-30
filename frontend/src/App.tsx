// Picks the page from the URL and the signed-in role: /careers/* is the public job board; staff need a login.
// Interviewers only get their interviews; admins can switch to the Users page; everyone else gets the board.
// ponytail: plain links + pathname switch, no router; add react-router when pages need nested layouts.
import { useCallback, useEffect, useState } from 'react'
import { Box } from '@mui/material'
import { api, session, UnauthorizedError, type UserBrief } from './api'
import UserBar from './components/UserBar'
import BoardPage from './pages/BoardPage'
import CareersPage from './pages/CareersPage'
import InterviewsPage from './pages/InterviewsPage'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/UsersPage'

export default function App() {
  const [user, setUser] = useState<UserBrief | null>(() => (session.token() ? session.user() : null))
  const [page, setPage] = useState<'board' | 'users'>('board')

  function signOut() {
    session.clear()
    setUser(null)
    setPage('board')
  }

  // request() already cleared the stored session on a 401; just drop back to the login page.
  const onError = useCallback((e: Error) => { if (e instanceof UnauthorizedError) setUser(null) }, [])

  // The stored role may be stale (admin changed it); refresh it once per load.
  const signedIn = user !== null
  useEffect(() => {
    if (!signedIn) return
    api.me().then((me) => { session.saveUser(me); setUser(me) })
      .catch(onError)
  }, [signedIn, onError])

  const match = window.location.pathname.match(/^\/careers(?:\/(\d+))?\/?$/)
  if (match) return <CareersPage jobId={match[1] ? Number(match[1]) : undefined} />
  if (!user) return <LoginPage onLoggedIn={setUser} />

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <UserBar user={user} page={page} onPage={setPage} onSignOut={signOut} />
      {user.role === 'interviewer' ? (
        <Box sx={{ p: 2 }}><InterviewsPage onError={onError} /></Box>
      ) : user.role === 'admin' && page === 'users' ? (
        <Box sx={{ p: 2 }}><UsersPage currentUserId={user.id} onError={onError} /></Box>
      ) : (
        <BoardPage onSignedOut={signOut} />
      )}
    </Box>
  )
}
