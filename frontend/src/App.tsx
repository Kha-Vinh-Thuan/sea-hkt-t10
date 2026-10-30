// Picks the page from the URL: /careers/* is the public job board; everything else needs a recruiter login.
// ponytail: plain links + pathname switch, no router; add react-router when pages need nested layouts.
import { useState } from 'react'
import { session } from './api'
import BoardPage from './pages/BoardPage'
import CareersPage from './pages/CareersPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  const [signedIn, setSignedIn] = useState(() => Boolean(session.token()))

  const match = window.location.pathname.match(/^\/careers(?:\/(\d+))?\/?$/)
  if (match) return <CareersPage jobId={match[1] ? Number(match[1]) : undefined} />
  if (!signedIn) return <LoginPage onLoggedIn={() => setSignedIn(true)} />
  return <BoardPage onSignedOut={() => { session.clear(); setSignedIn(false) }} />
}
