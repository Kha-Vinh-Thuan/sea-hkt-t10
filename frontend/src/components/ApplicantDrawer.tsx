// Side panel for one applicant: contact, stage, interviews, CV text, activity log.
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, CircularProgress, Divider, Drawer, IconButton, MenuItem, Stack, TextField, Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import DownloadIcon from '@mui/icons-material/Download'
import EventIcon from '@mui/icons-material/Event'
import { api, formatWhen, STAGE_LABEL, type ApplicantDetail, type Stage } from '../api'
import InterviewDialog from './InterviewDialog'

type Props = { applicantId?: number; stages: Stage[]; onClose: () => void; onChanged: () => void }

export default function ApplicantDrawer({ applicantId, stages, onClose, onChanged }: Props) {
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState<{ severity: 'success' | 'warning'; text: string } | null>(null)
  const [booking, setBooking] = useState(false)

  const reload = useCallback(async (id: number) => setApplicant(await api.applicant(id)), [])

  useEffect(() => {
    setApplicant(null)
    setError('')
    setNotice(null)
    if (applicantId !== undefined) reload(applicantId).catch((e: Error) => setError(e.message))
  }, [applicantId, reload])

  async function run(action: () => Promise<unknown>) {
    if (!applicant) return
    try {
      await action()
      await reload(applicant.id)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Drawer anchor="right" open={applicantId !== undefined} onClose={onClose}>
      <Box sx={{ width: { xs: '100vw', sm: 480 }, p: 3 }}>
        <Stack direction="row" sx={{ alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" fontWeight={700} sx={{ flex: 1 }}>{applicant?.name ?? 'Applicant'}</Typography>
          <IconButton onClick={onClose} aria-label="Close"><CloseIcon /></IconButton>
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
        {notice && <Alert severity={notice.severity} sx={{ mb: 2 }} onClose={() => setNotice(null)}>{notice.text}</Alert>}
        {!applicant && !error && <CircularProgress />}

        {applicant && (
          <Stack spacing={2}>
            <Box>
              <Typography>{applicant.email}</Typography>
              {applicant.phone && <Typography color="text.secondary">{applicant.phone}</Typography>}
            </Box>

            <TextField select label="Stage" value={applicant.stage}
              onChange={(e) => run(() => api.moveStage(applicant.id, e.target.value as Stage))}>
              {stages.map((s) => <MenuItem key={s} value={s}>{STAGE_LABEL[s]}</MenuItem>)}
            </TextField>

            <Stack direction="row" spacing={1}>
              <Button variant="contained" startIcon={<EventIcon />} onClick={() => setBooking(true)}>Schedule interview</Button>
              {applicant.cv_filename && (
                <Button variant="outlined" startIcon={<DownloadIcon />}
                  onClick={() => api.downloadCv(applicant.id, applicant.cv_filename).catch((e: Error) => setError(e.message))}>
                  CV
                </Button>
              )}
            </Stack>

            {applicant.interviews.length > 0 && (
              <>
                <Divider />
                <Typography variant="subtitle2" fontWeight={700}>Interviews</Typography>
                {applicant.interviews.map((i) => (
                  <Box key={i.id}>
                    <Typography variant="body2" fontWeight={600}>{formatWhen(i.start)}</Typography>
                    <Typography variant="caption" color="text.secondary" component="div">
                      {i.interviewer_name || i.interviewer_email}{i.location && ` · ${i.location}`}
                    </Typography>
                  </Box>
                ))}
              </>
            )}

            <Divider />
            <Typography variant="subtitle2" fontWeight={700}>CV text</Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-line', maxHeight: 320, overflow: 'auto' }}>
              {applicant.cv_text || 'No text could be extracted from this CV.'}
            </Typography>

            <Divider />
            <Typography variant="subtitle2" fontWeight={700}>Activity</Typography>
            {applicant.activity.map((a) => (
              <Box key={a.id}>
                <Typography variant="body2">{a.message}</Typography>
                <Typography variant="caption" color="text.secondary">{new Date(a.created_at).toLocaleString()}</Typography>
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      {applicant && (
        <InterviewDialog
          applicantId={applicant.id}
          open={booking}
          onClose={() => setBooking(false)}
          onBooked={({ emailed, mailError }) => {
            setBooking(false)
            setNotice(emailed
              ? { severity: 'success', text: 'Interview booked and invitation emailed.' }
              : { severity: 'warning', text: `Interview booked, but the email failed: ${mailError}` })
            run(async () => {})
          }}
        />
      )}
    </Drawer>
  )
}
