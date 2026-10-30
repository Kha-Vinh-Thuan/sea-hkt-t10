// Full page for one applicant (opened from a board card, Back returns to the board): header with contact and
// actions, a clickable stage bar, then two columns: interviews / CV text / activity on the left, recruiter fields,
// attachments, talent pools and other applications on the right.
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, LinearProgress, Link, Snackbar, Stack, Tooltip,
  Typography,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import DownloadIcon from '@mui/icons-material/Download'
import EmailIcon from '@mui/icons-material/EmailOutlined'
import EventIcon from '@mui/icons-material/Event'
import {
  api, daysInStage, isStuck, SOURCE_LABEL, STAGE_LABEL, type ApplicantDetail, type Stage, type StageRules,
} from '../api'
import { locale, t } from '../i18n'
import ActivityLog from '../components/ActivityLog'
import ApplicantFields from '../components/ApplicantFields'
import AttachmentList from '../components/AttachmentList'
import ComposeEmailDialog from '../components/ComposeEmailDialog'
import CopyToJobDialog from '../components/CopyToJobDialog'
import InterviewDialog from '../components/InterviewDialog'
import InterviewItem from '../components/InterviewItem'
import OtherApplications from '../components/OtherApplications'
import RefuseDialog from '../components/RefuseDialog'
import TalentPoolPicker from '../components/TalentPoolPicker'

type Props = { applicantId: number; stages: Stage[]; onBack: () => void; onOpen: (id: number) => void; onChanged: () => void }
type Notice = { severity: 'success' | 'warning'; text: string }

const today = () => new Date().toLocaleDateString('en-CA') // local YYYY-MM-DD, same format as the due date

function Section({ title, action, children }: { title?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <Card elevation={0} sx={{ boxShadow: '0 1px 3px rgba(15,23,42,.08)' }}>
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        {title && (
          <Stack direction="row" sx={{ alignItems: 'center', mb: 1.5 }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1 }}>{title}</Typography>
            {action}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  )
}

// A PDF shows in the browser's own viewer, like Odoo's; other formats fall back to the extracted text.
// ponytail: DOCX needs a server-side convert to PDF to preview; add it if recruiters ask.
function CvPreview({ id, filename, text }: { id: number; filename: string; text: string }) {
  const isPdf = filename.toLowerCase().endsWith('.pdf')
  const [url, setUrl] = useState<string>()
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (!isPdf) return
    let made: string | undefined
    let live = true
    api.cvUrl(id)
      .then((u) => { made = u; if (live) setUrl(u); else URL.revokeObjectURL(u) })
      .catch(() => { if (live) setFailed(true) })
    return () => { live = false; if (made) URL.revokeObjectURL(made); setUrl(undefined); setFailed(false) }
  }, [id, isPdf])
  if (url) {
    return <Box component="iframe" src={url} title={filename}
      sx={{ display: 'block', width: '100%', height: '80vh', minHeight: 560, border: 1, borderColor: 'divider', borderRadius: 1 }} />
  }
  if (isPdf && !failed) return <CircularProgress size={24} />
  return (
    <Typography variant="body2" sx={{ whiteSpace: 'pre-line', maxHeight: 480, overflow: 'auto' }}>
      {text || t('No text could be extracted from this CV.')}
    </Typography>
  )
}

// Odoo-style status bar: past stages filled, current one highlighted. `rejected` is only reachable through Refuse.
function StageBar({ stages, current, onMove }: { stages: Stage[]; current: Stage; onMove: (stage: Stage) => void }) {
  const shown = stages.filter((s) => s !== 'rejected' || s === current)
  const at = shown.indexOf(current)
  return (
    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }} role="group" aria-label={t('Stage')}>
      {shown.map((s, i) => (
        <Chip key={s} label={t(STAGE_LABEL[s])} clickable={s !== current && s !== 'rejected'}
          color={s === current ? (s === 'rejected' ? 'error' : 'primary') : 'default'}
          variant={i <= at ? 'filled' : 'outlined'} aria-current={s === current ? 'step' : undefined}
          onClick={s !== current && s !== 'rejected' ? () => onMove(s) : undefined}
          sx={{ px: 1, opacity: i < at ? 0.75 : 1 }} />
      ))}
    </Stack>
  )
}

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('').toUpperCase() || '?'
}

export default function ApplicantPage({ applicantId, stages, onBack, onOpen, onChanged }: Props) {
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState<Notice | null>(null)
  const [working, setWorking] = useState(false) // stage move, archive, …: thin bar on top of the header card
  const [booking, setBooking] = useState(false)
  const [refusing, setRefusing] = useState(false)
  const [copying, setCopying] = useState(false)
  const [composing, setComposing] = useState<{ stage?: Stage } | null>(null) // stage: offer that stage's template
  const [reasonLabels, setReasonLabels] = useState<Record<string, string>>({})
  const [requirements, setRequirements] = useState<StageRules['requirements']>()

  // Labels and stage hints come from the backend so the lists live in one place; both are hints only.
  useEffect(() => {
    api.refuseReasons().then((r) => setReasonLabels(Object.fromEntries(r.map((o) => [o.value, o.label])))).catch(() => {})
    api.stageRules().then((r) => setRequirements(r.requirements)).catch(() => {})
  }, [])

  const reload = useCallback(async (id: number) => setApplicant(await api.applicant(id)), [])

  useEffect(() => {
    setApplicant(null)
    setError('')
    setNotice(null)
    window.scrollTo(0, 0)
    reload(applicantId).catch((e: Error) => setError(e.message))
  }, [applicantId, reload])

  async function run(action: () => Promise<unknown>) {
    if (!applicant) return
    setWorking(true)
    try {
      await action()
      await reload(applicant.id)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setWorking(false)
    }
  }
  const refreshAll = () => run(async () => {})

  const back = <Button startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ mb: 2 }}>{t('Back to board')}</Button>
  if (!applicant) {
    return (
      <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1280, mx: 'auto' }}>
        {back}
        {error ? <Alert severity="error">{error}</Alert> : <CircularProgress sx={{ display: 'block' }} />}
      </Box>
    )
  }

  const a = applicant
  const overdue = a.next_action_due !== null && a.next_action_due < today()
  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1280, mx: 'auto' }}>
      {back}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {/* A toast, not an inline alert: the page may be scrolled far below the header when an action finishes. */}
      <Snackbar open={notice !== null} autoHideDuration={notice?.severity === 'success' ? 4000 : null}
        onClose={(_e, reason) => { if (reason !== 'clickaway') setNotice(null) }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        {notice ? <Alert severity={notice.severity} variant="filled" onClose={() => setNotice(null)}>{notice.text}</Alert> : undefined}
      </Snackbar>

      <Card elevation={0} sx={{ boxShadow: '0 1px 3px rgba(15,23,42,.08)', mb: 2 }}>
        <LinearProgress sx={{ visibility: working ? 'visible' : 'hidden' }} />
        <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ alignItems: { md: 'center' } }}>
            <Avatar sx={{ width: 64, height: 64, fontSize: 24, fontWeight: 700, bgcolor: 'primary.main' }}>{initials(a.name)}</Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="h5" fontWeight={800}>{a.name}</Typography>
              <Typography color="text.secondary" sx={{ wordBreak: 'break-all' }}>
                {a.email}{a.phone && ` · ${a.phone}`}
              </Typography>
              {a.linkedin && <Link href={a.linkedin} target="_blank" rel="noopener noreferrer" variant="body2">{a.linkedin}</Link>}
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75, mt: 1 }}>
                <Chip size="small" variant="outlined"
                  label={`${t('Source')}: ${t(SOURCE_LABEL[a.source])}${a.source_detail ? ` (${a.source_detail})` : ''}`} />
                {isStuck(a) && <Chip size="small" color="warning" label={t('Stuck in this stage')} />}
                {a.next_action && <Chip size="small" variant="outlined" label={`${t('Next')}: ${a.next_action}`} />}
                {a.next_action_due && (
                  <Chip size="small" color={overdue ? 'error' : 'default'}
                    label={`${overdue ? t('Overdue') : t('Due')} ${a.next_action_due}`} />
                )}
              </Stack>
            </Box>
            <Stack spacing={1} sx={{ alignItems: { md: 'flex-end' } }}>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, justifyContent: { md: 'flex-end' } }}>
                <Button variant="contained" startIcon={<EventIcon />} onClick={() => setBooking(true)}>{t('Schedule interview')}</Button>
                <Button variant="outlined" startIcon={<EmailIcon />} onClick={() => setComposing({})}>{t('Send email')}</Button>
                {a.cv_filename && (
                  <Button variant="outlined" startIcon={<DownloadIcon />}
                    onClick={() => api.downloadCv(a.id, a.cv_filename).catch((e: Error) => setError(e.message))}>CV</Button>
                )}
              </Stack>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, justifyContent: { md: 'flex-end' } }}>
                <Button size="small" startIcon={<ContentCopyIcon />} onClick={() => setCopying(true)}>{t('Copy to job')}</Button>
                {!a.archived && <Button size="small" onClick={() => run(() => api.archive(a.id))}>{t('Archive')}</Button>}
                {(a.archived || a.stage === 'rejected') && (
                  <Button size="small" onClick={() => run(() => api.restore(a.id))}>{t('Restore')}</Button>
                )}
                {a.stage !== 'rejected' && <Button size="small" color="error" onClick={() => setRefusing(true)}>{t('Refuse')}</Button>}
              </Stack>
            </Stack>
          </Stack>

          <Box sx={{ mt: 3 }}>
            <StageBar stages={stages} current={a.stage}
              onMove={(s) => run(async () => { await api.moveStage(a.id, s); setComposing({ stage: s }) })} />
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 1 }}>
              {t('In this stage for {days} days (since {when})',
                { days: daysInStage(a), when: new Date(a.stage_changed_at).toLocaleString(locale()) })}
            </Typography>
            {requirements?.[a.stage] && (
              <Tooltip title={t('A reminder only; it does not block moving the card.')}>
                <Alert severity="info" variant="outlined" sx={{ mt: 1.5 }}>{t('To move on')}: {requirements[a.stage]}</Alert>
              </Tooltip>
            )}
            {a.archived && <Alert severity="info" sx={{ mt: 1.5 }}>{t('Archived: hidden from the board.')}</Alert>}
            {a.refuse_reason && (
              <Alert severity="warning" sx={{ mt: 1.5 }}>{t('Refused')}: {reasonLabels[a.refuse_reason] ?? a.refuse_reason}</Alert>
            )}
          </Box>
          <Box sx={{ mt: 2, maxWidth: 420 }}>
            <TalentPoolPicker applicantId={a.id} onError={setError} onChanged={() => reload(a.id)} />
          </Box>
          {a.short_intro && (
            <Typography variant="body2" sx={{ whiteSpace: 'pre-line', mt: 2, color: 'text.secondary' }}>{a.short_intro}</Typography>
          )}
        </CardContent>
      </Card>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '3fr 2fr' }, alignItems: 'start' }}>
        <Stack spacing={2}>
          <Section title={t('Interviews')}
            action={<Button size="small" startIcon={<EventIcon />} onClick={() => setBooking(true)}>{t('Schedule')}</Button>}>
            {a.interviews.length === 0
              ? <Typography variant="body2" color="text.secondary">{t('No interviews yet.')}</Typography>
              : (
                <Stack spacing={2}>
                  {a.interviews.map((i) => (
                    <InterviewItem key={i.id} interview={i} onError={setError}
                      onChanged={(n) => { setNotice(n ?? null); refreshAll() }} />
                  ))}
                </Stack>
              )}
          </Section>

          <Section title={t('CV text')}>
            <CvPreview id={a.id} filename={a.cv_filename} text={a.cv_text} />
          </Section>

          <Section title={t('Activity')}>
            <ActivityLog items={a.activity} />
          </Section>
        </Stack>

        <Stack spacing={2}>
          <Section title={t('Recruiter notes')}>
            <ApplicantFields key={a.id} applicant={a} onError={setError}
              onSaved={() => { setNotice({ severity: 'success', text: t('Saved.') }); refreshAll() }} />
          </Section>
          <Section>
            <AttachmentList applicantId={a.id} items={a.attachments} onError={setError} onChanged={refreshAll} />
          </Section>
          {a.other_applications.length > 0 && (
            <Section><OtherApplications items={a.other_applications} onOpen={onOpen} /></Section>
          )}
        </Stack>
      </Box>

      <RefuseDialog applicantId={a.id} open={refusing} onClose={() => setRefusing(false)}
        onRefused={({ emailed, mailError, sendEmail }) => {
          setRefusing(false)
          setNotice(!sendEmail || emailed
            ? { severity: 'success', text: emailed ? t('Applicant refused and emailed.') : t('Applicant refused.') }
            : { severity: 'warning', text: t('Applicant refused, but the email failed: {error}', { error: mailError ?? '' }) })
          refreshAll()
        }} />
      <CopyToJobDialog applicant={a} open={copying} onClose={() => setCopying(false)}
        onCopied={(_copy, jobTitle) => {
          setCopying(false)
          setNotice({ severity: 'success', text: t('Copied to {job}.', { job: jobTitle }) })
          refreshAll() // "Also applied to" now lists the copy
        }} />
      {composing && (
        <ComposeEmailDialog applicantId={a.id} stage={composing.stage} onClose={() => setComposing(null)}
          onSent={({ sent, error: mailError }) => {
            setComposing(null)
            setNotice(sent ? { severity: 'success', text: t('Email sent.') }
              : { severity: 'warning', text: t('Email not sent: {error}', { error: mailError ?? '' }) })
            refreshAll() // activity log shows the email
          }} />
      )}
      <InterviewDialog applicantId={a.id} open={booking} onClose={() => setBooking(false)}
        onBooked={({ emailed, mailError, proposed }) => {
          const what = proposed ? t('Times proposed') : t('Interview booked')
          setBooking(false)
          setNotice(emailed
            ? { severity: 'success', text: t('{what} and emailed to the candidate.', { what }) }
            : { severity: 'warning', text: t('{what}, but the email failed: {error}', { what, error: mailError ?? '' }) })
          refreshAll()
        }} />
    </Box>
  )
}
