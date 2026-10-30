// Upcoming interviews across all jobs, soonest first.
import { useEffect, useState } from 'react'
import {
  Alert, Card, CardContent, CircularProgress, Link, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from '@mui/material'
import { api, formatWhen, type UpcomingInterview } from '../api'

export default function InterviewsPage({ onError }: { onError: (e: Error) => void }) {
  const [rows, setRows] = useState<UpcomingInterview[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.interviews().then(setRows).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!rows) return <CircularProgress />
  if (!rows.length) return <Typography color="text.secondary">No upcoming interviews.</Typography>

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
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
