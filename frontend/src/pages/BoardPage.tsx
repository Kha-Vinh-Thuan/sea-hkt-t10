// Recruiter area: "Pipeline" (jobs + applicants by stage), "Interviews" (upcoming list), "Reports", "Talent pools".
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, List, ListItemButton, ListItemText, Paper, Stack, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import {
  api, loadStageRules, STAGE_LABEL, UnauthorizedError, type Applicant, type ApplicantFilters, type Job, type Stage, type UserBrief,
} from '../api'
import { t } from '../i18n'
import BoardFilters from '../components/BoardFilters'
import ComposeEmailDialog from '../components/ComposeEmailDialog'
import JobDialog from '../components/JobDialog'
import RefuseDialog from '../components/RefuseDialog'
import StageColumn from '../components/StageColumn'
import ApplicantPage from './ApplicantPage'
import InterviewsPage from './InterviewsPage'
import ReportsPage from './ReportsPage'
import TalentPoolsPage from './TalentPoolsPage'

export type BoardTab = 'pipeline' | 'interviews' | 'reports' | 'pools'

// The tab comes from the NavBar (App owns it) so the top bar stays one strip for every staff page.
export default function BoardPage({ tab, onTab, onSignedOut }: {
  tab: BoardTab; onTab: (tab: BoardTab) => void; onSignedOut: () => void
}) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [stages, setStages] = useState<Stage[]>([])
  const [users, setUsers] = useState<UserBrief[]>([])
  const [applicants, setApplicants] = useState<Applicant[] | null>(null)
  const [jobId, setJobId] = useState<number>()
  const [openId, setOpenId] = useState<number>()
  // The applicant page is a history entry, so the browser's Back button returns to the board too.
  const openApplicant = useCallback((id: number) => { window.history.pushState({ applicant: id }, ''); setOpenId(id) }, [])
  const closeApplicant = useCallback(() => { if (window.history.state?.applicant) window.history.back(); else setOpenId(undefined) }, [])
  useEffect(() => {
    const onPop = () => setOpenId(window.history.state?.applicant)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  // Picking a section in the NavBar leaves the applicant page.
  useEffect(() => { setOpenId(undefined) }, [tab])
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
      .then(([j, s, u]) => { setStages(s); setUsers(u); setJobId((id) => id ?? j[0]?.id) })
      .catch(fail)
  }, [loadJobs, fail])

  useEffect(() => {
    if (jobId === undefined) return
    setApplicants(null)
    // Switching jobs quickly: a slower answer for the previous job must not overwrite this one.
    let current = true
    api.applicants(jobId, filters).then((rows) => { if (current) setApplicants(rows) }).catch(fail)
    return () => { current = false }
  }, [jobId, filters, fail])

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

      {error && <Alert severity="error" sx={{ m: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {openId !== undefined ? (
        <ApplicantPage applicantId={openId} stages={stages} onBack={closeApplicant} onOpen={openApplicant}
          onChanged={refresh} />
      ) : tab === 'interviews' ? (
        <Box sx={{ p: 2 }}><InterviewsPage onError={fail} /></Box>
      ) : tab === 'reports' ? (
        <Box sx={{ p: 2 }}><ReportsPage onError={fail} /></Box>
      ) : tab === 'pools' ? (
        <Box sx={{ p: 2 }}><TalentPoolsPage onError={fail} /></Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' } }}>
          <Paper elevation={0} sx={{ width: { md: 290 }, m: 2, mr: { md: 0 }, py: 0.5, borderRadius: 4, flexShrink: 0,
            alignSelf: 'flex-start', boxShadow: '0 1px 3px rgba(15,23,42,.08)' }}>
            <Stack direction="row" sx={{ px: 2, pt: 1.5, alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="overline" color="text.secondary">{t('Job positions')}</Typography>
              <Button size="small" startIcon={<AddIcon />} onClick={() => setDialog('new')}>{t('New job')}</Button>
            </Stack>
            <List dense>
              {jobs.map((job) => (
                <ListItemButton key={job.id} selected={job.id === jobId} onClick={() => setJobId(job.id)}>
                  <ListItemText primary={job.title} slotProps={{ primary: { fontWeight: 600 } }}
                    secondary={`${job.is_open ? t('Open') : t('Closed')} · ${t('{hired} / {openings} hired', { hired: job.hired_count, openings: job.openings })}${recruiterOf(job)}`} />
                  <Chip size="small" label={job.applicant_count} color={job.id === jobId ? 'primary' : 'default'} />
                </ListItemButton>
              ))}
            </List>
          </Paper>

          <Box sx={{ flex: 1, p: 2, px: { md: 3 }, overflowX: 'auto' }}>
            {selectedJob && (
              <Stack direction="row" spacing={1.5} sx={{ mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                <Typography variant="h6" fontWeight={700}>{selectedJob.title}</Typography>
                <Chip size="small" color={selectedJob.hired_count >= selectedJob.openings ? 'success' : 'default'}
                  label={t('{hired} / {openings} hired', { hired: selectedJob.hired_count, openings: selectedJob.openings })} />
                <Button size="small" startIcon={<EditOutlinedIcon />} onClick={() => setDialog(selectedJob)}>{t('Edit job')}</Button>
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
                      <ListItemButton key={a.id} onClick={() => openApplicant(a.id)}>
                        <ListItemText primary={a.name} secondary={a.email} />
                        <Chip size="small" label={t(STAGE_LABEL[a.stage])} />
                      </ListItemButton>
                    ))}
                    {!applicants.length && <ListItemText sx={{ px: 2 }} secondary={t('No archived applicants.')} />}
                  </List>
                </Paper>
              ) : (
                <Stack direction="row" spacing={2} sx={{ alignItems: 'flex-start' }}>
                  {stages.map((stage) => (
                    <StageColumn key={stage} stage={stage} items={applicants.filter((a) => a.stage === stage)}
                      onOpen={openApplicant} onDropApplicant={dropApplicant} />
                  ))}
                </Stack>
              )
            )}
          </Box>
        </Box>
      )}

      {refusingId !== undefined && (
        <RefuseDialog applicantId={refusingId} open onClose={() => setRefusingId(undefined)}
          onRefused={({ emailed, mailError, sendEmail }) => {
            setRefusingId(undefined)
            if (sendEmail && !emailed) setError(t('Applicant refused, but the email failed: {error}', { error: mailError ?? '' }))
            refresh()
          }} />
      )}
      {composing && (
        <ComposeEmailDialog key={`${composing.id}-${composing.stage}`} applicantId={composing.id} stage={composing.stage}
          onClose={() => setComposing(undefined)}
          onSent={({ sent, error }) => { setComposing(undefined); if (!sent) setError(t('Email not sent: {error}', { error: error ?? '' })) }} />
      )}
      <JobDialog
        key={dialog === 'new' ? 'new' : dialog?.id}
        open={dialog !== null}
        job={dialog === 'new' || dialog === null ? undefined : dialog}
        onClose={() => setDialog(null)}
        onSaved={(job) => { setDialog(null); onTab('pipeline'); loadJobs().then(() => setJobId(job.id)).catch(fail) }}
      />
    </Box>
  )
}
