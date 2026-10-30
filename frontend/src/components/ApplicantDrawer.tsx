// Side panel for one applicant: contact, stage selector, CV text, activity log.
import { useEffect, useState } from 'react'
import {
  Alert, Box, Button, CircularProgress, Divider, Drawer, IconButton, MenuItem, Stack, TextField, Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import DownloadIcon from '@mui/icons-material/Download'
import { api, STAGE_LABEL, type ApplicantDetail, type Stage } from '../api'

type Props = { applicantId?: number; stages: Stage[]; onClose: () => void; onChanged: () => void }

export default function ApplicantDrawer({ applicantId, stages, onClose, onChanged }: Props) {
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setApplicant(null)
    setError('')
    if (applicantId !== undefined) api.applicant(applicantId).then(setApplicant).catch((e: Error) => setError(e.message))
  }, [applicantId])

  async function changeStage(stage: Stage) {
    if (!applicant) return
    try {
      await api.moveStage(applicant.id, stage)
      setApplicant(await api.applicant(applicant.id))
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

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {!applicant && !error && <CircularProgress />}

        {applicant && (
          <Stack spacing={2}>
            <Box>
              <Typography>{applicant.email}</Typography>
              {applicant.phone && <Typography color="text.secondary">{applicant.phone}</Typography>}
            </Box>

            <TextField select label="Stage" value={applicant.stage} onChange={(e) => changeStage(e.target.value as Stage)}>
              {stages.map((s) => <MenuItem key={s} value={s}>{STAGE_LABEL[s]}</MenuItem>)}
            </TextField>

            {applicant.cv_filename && (
              <Button href={api.cvUrl(applicant.id)} startIcon={<DownloadIcon />} variant="outlined">
                {applicant.cv_filename}
              </Button>
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
    </Drawer>
  )
}
