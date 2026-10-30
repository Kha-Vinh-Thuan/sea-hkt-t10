// Recruitment summary per job (GET /reports/summary): pipeline by stage, hired vs openings, days to hire,
// then where applicants came from and why they were refused. Plain tables, no chart library.
import { useEffect, useState } from 'react'
import {
  Alert, Box, Card, CardContent, CircularProgress, LinearProgress, Stack, Table, TableBody, TableCell, TableHead,
  TableRow, Typography,
} from '@mui/material'
import { api, SOURCE_LABEL, STAGE_LABEL, type JobReport } from '../api'

// One table: a row per job, a column per key of the chosen count map.
function CountTable<K extends string>({ title, rows, labels, counts }: {
  title: string; rows: JobReport[]; labels: Record<K, string>; counts: (r: JobReport) => Record<K, number>
}) {
  const keys = Object.keys(labels) as K[]
  return (
    <Card variant="outlined">
      <CardContent sx={{ overflowX: 'auto' }}>
        <Typography variant="subtitle1" fontWeight={700} gutterBottom>{title}</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Job</TableCell>
              {keys.map((k) => <TableCell key={k} align="right">{labels[k]}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.job_id}>
                <TableCell>{r.title}</TableCell>
                {keys.map((k) => (
                  <TableCell key={k} align="right" sx={{ color: counts(r)[k] ? undefined : 'text.disabled' }}>
                    {counts(r)[k]}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default function ReportsPage({ onError }: { onError: (e: Error) => void }) {
  const [rows, setRows] = useState<JobReport[] | null>(null)
  const [error, setError] = useState('')
  const [reasonLabels, setReasonLabels] = useState<Record<string, string>>({})

  useEffect(() => {
    // Refuse reason labels live in the backend (GET /refuse-reasons).
    api.refuseReasons().then((r) => setReasonLabels(Object.fromEntries(r.map((o) => [o.value, o.label])))).catch(() => {})
    api.reportSummary().then(setRows).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!rows) return <CircularProgress />
  if (!rows.length) return <Typography color="text.secondary">No jobs yet.</Typography>

  return (
    <Stack spacing={2}>
      <Card variant="outlined">
        <CardContent sx={{ overflowX: 'auto' }}>
          <Typography variant="subtitle1" fontWeight={700} gutterBottom>Hiring progress</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Job</TableCell>
                <TableCell align="right">Applicants</TableCell>
                <TableCell sx={{ minWidth: 160 }}>Hired / openings</TableCell>
                <TableCell align="right">Avg days to hire</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.job_id}>
                  <TableCell>{r.title}{!r.is_open && ' (closed)'}</TableCell>
                  <TableCell align="right">{r.total}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress variant="determinate" sx={{ flex: 1 }}
                        color={r.hired >= r.openings ? 'success' : 'primary'}
                        value={r.openings ? Math.min(100, (100 * r.hired) / r.openings) : 0} />
                      <Typography variant="body2">{r.hired} / {r.openings}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="right">{r.avg_days_to_hire ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <CountTable title="Applicants by stage" rows={rows} labels={STAGE_LABEL} counts={(r) => r.by_stage} />
      <CountTable title="Applicants by source" rows={rows} labels={SOURCE_LABEL} counts={(r) => r.by_source} />
      <CountTable title="Refused by reason" rows={rows} labels={reasonLabels} counts={(r) => r.refused_by_reason} />
    </Stack>
  )
}
