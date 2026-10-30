// Recruiter area: "Pipeline" (jobs + applicants by stage), "Interviews" (upcoming list), "Reports", "Talent pools".
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, AppBar, Box, Button, Chip, CircularProgress, List, ListItemButton, ListItemText, Paper, Stack, Tab,
  Tabs, Toolbar, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline'
import {
  api, loadStageRules, STAGE_LABEL, UnauthorizedError, type Applicant, type ApplicantFilters, type Job, type Stage, type UserBrief,
} from '../api'
import ApplicantDrawer from '../components/ApplicantDrawer'
import BoardFilters from '../components/BoardFilters'
import ComposeEmailDialog from '../components/ComposeEmailDialog'
import JobDialog from '../components/JobDialog'
import RefuseDialog from '../components/RefuseDialog'
import StageColumn from '../components/StageColumn'
import InterviewsPage from './InterviewsPage'
import ReportsPage from './ReportsPage'
import TalentPoolsPage from './TalentPoolsPage'

export default function BoardPage({ onSignedOut }: { onSignedOut: () => void }) {
  const [tab, setTab] = useState<'pipeline' | 'interviews' | 'reports' | 'pools'>('pipeline')
  const [jobs, setJobs] = useState<Job[]>([])
  const [stages, setStages] = useState<Stage[]>([])
  const [users, setUsers] = useState<UserBrief[]>([])
  const [applicants, setApplicants] = useState<Applicant[] | null>(null)
  const [jobId, setJobId] = useState<number>()
  const [openId, setOpenId] = useState<number>()
  const [dialog, setDialog] = useState<'new' | Job | null>(null)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<ApplicantFilters>({})
  const [refusingId, setRefusingId] = useState<number>()
  const [composing, setComposing] = useState<{ id: number; stage: Stage }>() // after a drag: offer the stage's template

  // An expired or invalid token sends the recruiter back to the login page instead of showing an error.
  const fail = useCallback((e: Error) => (e instanceof UnauthorizedError ? onSignedOut() : setError(e.message)), [onSignedOut])
  const loadJobs = useCallback(() => api.jobs().then((j) => { setJobs(j); return j }), [])
  const loadApplicants = useCallback((id: number) => api.applicants(id, filters).then(setApplicants), [filters])

  useEffect(() => {
    Promise.all([loadJobs(), api.stages(), api.users(), loadStageRules()])
      .then(([j, s, u]) => { setStages(s); setUsers(u); setJobId(j[0]?.id) })
      .catch(fail)
  }, [loadJobs, fail])

  useEffect(() => {
    if (jobId === undefined) return
    setApplicants(null)
    loadApplicants(jobId).catch(fail)
  }, [jobId, loadApplicants, fail])

  const selectedJob = jobs.find((j) => j.id === jobId)
  const recruiterOf = (job: Job) => {
    const u = users.find((x) => x.id === job.recruiter_id)
    return u ? ` · ${u.name || u.email}` : ''
  }

  function refresh() {
    if (jobId !== undefined) loadApplicants(jobId).catch(fail)
    loadJobs().catch(fail)
  }

  // Dropping on `rejected` goes through Refuse so a reason is recorded; other moves are optimistic with rollback.
  async function dropApplicant(id: number, stage: Stage) {
    const before = applicants
    const moved = before?.find((a) => a.id === id)
    if (!before || !moved || moved.stage === stage) return
    if (stage === 'rejected') return setRefusingId(id)
    setApplicants(before.map((a) => (a.id === id ? { ...a, stage } : a)))
    try {
      await api.moveStage(id, stage)
      refresh() // job counters (hired) may have changed
      setComposing({ id, stage })
    } catch (e) {
      setApplicants(before)
      fail(e as Error)
    }
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
            <Tab value="reports" label="Reports" />
            <Tab value="pools" label="Talent pools" />
          </Tabs>
          <Button href="/careers" target="_blank" endIcon={<OpenInNewIcon />}>Careers site</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog('new')}>New job</Button>
        </Toolbar>
      </AppBar>

      {error && <Alert severity="error" sx={{ m: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {tab === 'interviews' ? (
        <Box sx={{ p: 2 }}><InterviewsPage onError={fail} /></Box>
      ) : tab === 'reports' ? (
        <Box sx={{ p: 2 }}><ReportsPage onError={fail} /></Box>
      ) : tab === 'pools' ? (
        <Box sx={{ p: 2 }}><TalentPoolsPage onError={fail} /></Box>
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
                    secondary={`${job.is_open ? job.department || 'Open' : 'Closed'} · ${job.hired_count} / ${job.openings} hired${recruiterOf(job)}`} />
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
            <BoardFilters value={filters} onChange={setFilters} />
            {applicants === null ? (
              jobs.length || error ? <CircularProgress sx={{ m: 4 }} /> : null
            ) : (
              filters.archived ? (
                // Archived applicants are off the board; open one to restore it from the drawer.
                <Paper variant="outlined">
                  <List dense>
                    {applicants.map((a) => (
                      <ListItemButton key={a.id} onClick={() => setOpenId(a.id)}>
                        <ListItemText primary={a.name} secondary={a.email} />
                        <Chip size="small" label={STAGE_LABEL[a.stage]} />
                      </ListItemButton>
                    ))}
                    {!applicants.length && <ListItemText sx={{ px: 2 }} secondary="No archived applicants." />}
                  </List>
                </Paper>
              ) : (
                <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
                  {stages.map((stage) => (
                    <StageColumn key={stage} stage={stage} items={applicants.filter((a) => a.stage === stage)}
                      onOpen={setOpenId} onDropApplicant={dropApplicant} />
                  ))}
                </Stack>
              )
            )}
          </Box>
        </Box>
      )}

      <ApplicantDrawer applicantId={openId} stages={stages} onClose={() => setOpenId(undefined)} onChanged={refresh} />
      {refusingId !== undefined && (
        <RefuseDialog applicantId={refusingId} open onClose={() => setRefusingId(undefined)}
          onRefused={({ emailed, mailError, sendEmail }) => {
            setRefusingId(undefined)
            if (sendEmail && !emailed) setError(`Applicant refused, but the email failed: ${mailError}`)
            refresh()
          }} />
      )}
      {composing && (
        <ComposeEmailDialog key={`${composing.id}-${composing.stage}`} applicantId={composing.id} stage={composing.stage}
          onClose={() => setComposing(undefined)}
          onSent={({ sent, error }) => { setComposing(undefined); if (!sent) setError(`Email not sent: ${error}`) }} />
      )}
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
