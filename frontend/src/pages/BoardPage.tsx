// Recruiter area: "Pipeline" (jobs + applicants by stage) and "Interviews" (upcoming list).
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, AppBar, Avatar, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, IconButton, List,
  ListItemButton, ListItemText, Paper, Stack, Tab, Tabs, Toolbar, Tooltip, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import LogoutIcon from '@mui/icons-material/Logout'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline'
import { api, STAGE_LABEL, UnauthorizedError, type Applicant, type Job, type Stage } from '../api'
import ApplicantDrawer from '../components/ApplicantDrawer'
import JobDialog from '../components/JobDialog'
import InterviewsPage from './InterviewsPage'

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('').toUpperCase() || '?'
}

export default function BoardPage({ onSignedOut }: { onSignedOut: () => void }) {
  const [tab, setTab] = useState<'pipeline' | 'interviews'>('pipeline')
  const [jobs, setJobs] = useState<Job[]>([])
  const [stages, setStages] = useState<Stage[]>([])
  const [applicants, setApplicants] = useState<Applicant[] | null>(null)
  const [jobId, setJobId] = useState<number>()
  const [openId, setOpenId] = useState<number>()
  const [dialog, setDialog] = useState<'new' | Job | null>(null)
  const [error, setError] = useState('')

  // An expired or invalid token sends the recruiter back to the login page instead of showing an error.
  const fail = useCallback((e: Error) => (e instanceof UnauthorizedError ? onSignedOut() : setError(e.message)), [onSignedOut])
  const loadJobs = useCallback(() => api.jobs().then((j) => { setJobs(j); return j }), [])
  const loadApplicants = useCallback((id: number) => api.applicants(id).then(setApplicants), [])

  useEffect(() => {
    Promise.all([loadJobs(), api.stages()])
      .then(([j, s]) => { setStages(s); setJobId(j[0]?.id) })
      .catch(fail)
  }, [loadJobs, fail])

  useEffect(() => {
    if (jobId === undefined) return
    setApplicants(null)
    loadApplicants(jobId).catch(fail)
  }, [jobId, loadApplicants, fail])

  const selectedJob = jobs.find((j) => j.id === jobId)

  function refresh() {
    if (jobId !== undefined) loadApplicants(jobId).catch(fail)
    loadJobs().catch(fail)
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" elevation={0} color="inherit" sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 1, flexWrap: 'wrap' }}>
          <WorkOutlineIcon color="primary" />
          <Typography variant="h6" fontWeight={700} sx={{ mr: 2 }}>Recruitment</Typography>
          <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ flex: 1 }}>
            <Tab value="pipeline" label="Pipeline" />
            <Tab value="interviews" label="Interviews" />
          </Tabs>
          <Button href="/careers" target="_blank" endIcon={<OpenInNewIcon />}>Careers site</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog('new')}>New job</Button>
          <Tooltip title="Sign out">
            <IconButton onClick={onSignedOut} aria-label="Sign out"><LogoutIcon /></IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {error && <Alert severity="error" sx={{ m: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {tab === 'interviews' ? (
        <Box sx={{ p: 2 }}><InterviewsPage onError={fail} /></Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' } }}>
          <Paper square elevation={0} sx={{ width: { md: 280 }, borderRight: { md: 1 }, borderColor: 'divider', flexShrink: 0 }}>
            <Typography variant="overline" color="text.secondary" sx={{ px: 2, pt: 2, display: 'block' }}>
              Job positions
            </Typography>
            <List dense>
              {jobs.map((job) => (
                <ListItemButton key={job.id} selected={job.id === jobId} onClick={() => setJobId(job.id)}>
                  <ListItemText primary={job.title}
                    secondary={`${job.is_open ? job.department || 'Open' : 'Closed'} · ${job.hired_count} / ${job.openings} hired`} />
                  <Chip size="small" label={job.applicant_count} />
                </ListItemButton>
              ))}
            </List>
          </Paper>

          <Box sx={{ flex: 1, p: 2, overflowX: 'auto' }}>
            {selectedJob && (
              <Stack direction="row" spacing={1.5} sx={{ mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                <Typography variant="h6" fontWeight={700}>{selectedJob.title}</Typography>
                <Chip size="small" color={selectedJob.hired_count >= selectedJob.openings ? 'success' : 'default'}
                  label={`${selectedJob.hired_count} / ${selectedJob.openings} hired`} />
                <Button size="small" startIcon={<EditOutlinedIcon />} onClick={() => setDialog(selectedJob)}>Edit job</Button>
              </Stack>
            )}
            {applicants === null ? (
              jobs.length || error ? <CircularProgress sx={{ m: 4 }} /> : null
            ) : (
              <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
                {stages.map((stage) => {
                  const items = applicants.filter((a) => a.stage === stage)
                  return (
                    <Paper key={stage} variant="outlined" sx={{ width: 260, flexShrink: 0, p: 1.5, bgcolor: 'action.hover' }}>
                      <Stack direction="row" sx={{ mb: 1.5, alignItems: 'center', justifyContent: 'space-between' }}>
                        <Typography variant="subtitle2" fontWeight={700}>{STAGE_LABEL[stage]}</Typography>
                        <Chip size="small" label={items.length} />
                      </Stack>
                      <Stack spacing={1}>
                        {items.map((a) => (
                          <Card key={a.id} variant="outlined">
                            <CardActionArea onClick={() => setOpenId(a.id)}>
                              <CardContent sx={{ display: 'flex', gap: 1.5, alignItems: 'center', '&:last-child': { pb: 2 } }}>
                                <Avatar sx={{ width: 36, height: 36, fontSize: 14 }}>{initials(a.name)}</Avatar>
                                <Box sx={{ minWidth: 0 }}>
                                  <Typography variant="subtitle2" noWrap>{a.name}</Typography>
                                  <Typography variant="caption" color="text.secondary" noWrap component="div">{a.email}</Typography>
                                </Box>
                              </CardContent>
                            </CardActionArea>
                          </Card>
                        ))}
                      </Stack>
                    </Paper>
                  )
                })}
              </Stack>
            )}
          </Box>
        </Box>
      )}

      <ApplicantDrawer applicantId={openId} stages={stages} onClose={() => setOpenId(undefined)} onChanged={refresh} />
      <JobDialog
        key={dialog === 'new' ? 'new' : dialog?.id}
        open={dialog !== null}
        job={dialog === 'new' || dialog === null ? undefined : dialog}
        onClose={() => setDialog(null)}
        onSaved={(job) => { setDialog(null); setTab('pipeline'); loadJobs().then(() => setJobId(job.id)).catch(fail) }}
      />
    </Box>
  )
}
