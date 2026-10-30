// Picks the page from the URL: /careers/* is the public job board, everything else is the recruiter board.
// ponytail: plain links + pathname switch, no router; add react-router when pages need nested layouts.
import CareersPage from './pages/CareersPage'
import BoardPage from './pages/BoardPage'

export default function App() {
  const match = window.location.pathname.match(/^\/careers(?:\/(\d+))?\/?$/)
  if (match) return <CareersPage jobId={match[1] ? Number(match[1]) : undefined} />
  return <BoardPage />
}
