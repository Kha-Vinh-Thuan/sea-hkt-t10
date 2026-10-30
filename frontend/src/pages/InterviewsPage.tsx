// Interviews list, soonest first: upcoming ones for recruiters, all of their own for an interviewer (server decides).
// Started, non-cancelled interviews get a Feedback action.
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Chip, CardContent, CircularProgress, Link, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material'
import { api, formatWhen, INTERVIEW_STATUS_COLOR, INTERVIEW_STATUS_LABEL, type UpcomingInterview } from '../api'
import FeedbackDialog from '../components/FeedbackDialog'

export default function InterviewsPage({ onError }: { onError: (e: Error) => void }) {
  const [rows, setRows] = useState<UpcomingInterview[] | null>(null)
  const [error, setError] = useState('')
  const [feedbackFor, setFeedbackFor] = useState<UpcomingInterview>()

  const load = useCallback(() => {
    api.interviews().then(setRows).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])
  useEffect(load, [load])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!rows) return <CircularProgress />
  if (!rows.length) return <Typography color="text.secondary">No interviews.</Typography>

  return (
    <Card variant="outlined">
      <CardContent sx={{ overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>When</TableCell>
              <TableCell>Candidate</TableCell>
              <TableCell>Job</TableCell>
              <TableCell>Interviewer</TableCell>
              <TableCell>Where</TableCell>
              <TableCell>Status</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((i) => (
              <TableRow key={i.id}>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Stack>
                    <Typography variant="body2" fontWeight={600}>{formatWhen(i.start)}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      until {new Date(i.end).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{i.applicant_name}</TableCell>
                <TableCell>{i.job_title}</TableCell>
                <TableCell>{i.interviewer_name || i.interviewer_email}</TableCell>
                <TableCell>
                  {i.location.startsWith('http')
                    ? <Link href={i.location} target="_blank" rel="noopener">Join</Link>
                    : i.location || '—'}
                </TableCell>
                <TableCell>
                  <Chip size="small" label={INTERVIEW_STATUS_LABEL[i.status]} color={INTERVIEW_STATUS_COLOR[i.status]} />
                </TableCell>
                <TableCell>
                  {new Date(i.start).getTime() <= Date.now() && i.status !== 'cancelled' && (
                    <Button size="small" onClick={() => setFeedbackFor(i)}>Feedback</Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {feedbackFor && (
          <FeedbackDialog interview={feedbackFor} open onClose={() => setFeedbackFor(undefined)}
            onSaved={() => { setFeedbackFor(undefined); load() }} />
        )}
      </CardContent>
    </Card>
  )
}
