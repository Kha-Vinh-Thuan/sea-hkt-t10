// Side panel for one applicant: contact, stage, refuse / archive / copy to job, interviews, attachments, recruiter
// fields, CV text, activity log.
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, Divider, Drawer, IconButton, Link, MenuItem, Stack, TextField, Typography,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import DownloadIcon from '@mui/icons-material/Download'
import EmailIcon from '@mui/icons-material/EmailOutlined'
import EventIcon from '@mui/icons-material/Event'
import {
  api, daysInStage, isStuck, SOURCE_LABEL, STAGE_LABEL, type ApplicantDetail, type Stage, type StageRules,
} from '../api'
import ApplicantFields from './ApplicantFields'
import ComposeEmailDialog from './ComposeEmailDialog'
import AttachmentList from './AttachmentList'
import CopyToJobDialog from './CopyToJobDialog'
import InterviewDialog from './InterviewDialog'
import InterviewItem from './InterviewItem'
import OtherApplications from './OtherApplications'
import RefuseDialog from './RefuseDialog'
import TalentPoolPicker from './TalentPoolPicker'

type Props = { applicantId?: number; stages: Stage[]; onClose: () => void; onChanged: () => void }

const today = () => new Date().toLocaleDateString('en-CA') // local YYYY-MM-DD, same format as the due date

export default function ApplicantDrawer({ applicantId: openedId, stages, onClose, onChanged }: Props) {
  // "Also applied to" links switch the drawer to another applicant without the board knowing;
  // the switch only counts while the board still has the same applicant open.
  const [switched, setSwitched] = useState<{ from?: number; to: number } | null>(null)
  const applicantId = switched && switched.from === openedId ? switched.to : openedId
  // Forget the switch on close, so reopening the same card shows that card again.
  const close = () => { setSwitched(null); onClose() }
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState<{ severity: 'success' | 'warning'; text: string } | null>(null)
  const [booking, setBooking] = useState(false)
  const [refusing, setRefusing] = useState(false)
  const [reasonLabels, setReasonLabels] = useState<Record<string, string>>({})

  // Labels come from the backend so the list lives in one place.
  useEffect(() => {
    api.refuseReasons().then((r) => setReasonLabels(Object.fromEntries(r.map((o) => [o.value, o.label])))).catch(() => {})
  }, [])
  const [requirements, setRequirements] = useState<StageRules['requirements']>()

  useEffect(() => { api.stageRules().then((r) => setRequirements(r.requirements)).catch(() => {}) }, []) // hint only
  const [copying, setCopying] = useState(false)
  const [composing, setComposing] = useState<{ stage?: Stage } | null>(null) // stage: offer that stage's template

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
    <Drawer anchor="right" open={applicantId !== undefined} onClose={close}>
      <Box sx={{ width: { xs: '100vw', sm: 480 }, p: 3 }}>
        <Stack direction="row" sx={{ alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" fontWeight={700} sx={{ flex: 1 }}>{applicant?.name ?? 'Applicant'}</Typography>
          <IconButton onClick={close} aria-label="Close"><CloseIcon /></IconButton>
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
        {notice && <Alert severity={notice.severity} sx={{ mb: 2 }} onClose={() => setNotice(null)}>{notice.text}</Alert>}
        {!applicant && !error && <CircularProgress />}

        {applicant && (
          <Stack spacing={2}>
            <Box>
              <Typography>{applicant.email}</Typography>
              {applicant.phone && <Typography color="text.secondary">{applicant.phone}</Typography>}
              {applicant.linkedin && (
                <Link href={applicant.linkedin} target="_blank" rel="noopener noreferrer">{applicant.linkedin}</Link>
              )}
              {applicant.short_intro && (
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line', mt: 1 }}>{applicant.short_intro}</Typography>
              )}
            </Box>

            {applicant.archived && <Alert severity="info">Archived: hidden from the board.</Alert>}
            {applicant.refuse_reason && (
              <Alert severity="warning">Refused: {reasonLabels[applicant.refuse_reason] ?? applicant.refuse_reason}</Alert>
            )}

            {/* `rejected` is only reachable through Refuse, so a reason is always recorded. */}
            <TextField select label="Stage" value={applicant.stage}
              helperText={`In this stage for ${daysInStage(applicant)} days (since ${new Date(applicant.stage_changed_at).toLocaleString()})`}
              onChange={(e) => { const s = e.target.value as Stage; run(async () => { await api.moveStage(applicant.id, s); setComposing({ stage: s }) }) }}>
              {stages.filter((s) => s !== 'rejected' || s === applicant.stage).map((s) => (
                <MenuItem key={s} value={s} disabled={s === 'rejected'}>{STAGE_LABEL[s]}</MenuItem>
              ))}
            </TextField>
            {requirements?.[applicant.stage] && (
              <Alert severity="info" variant="outlined">To move on: {requirements[applicant.stage]}</Alert>
            )}

            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {isStuck(applicant) && <Chip size="small" color="warning" label="Stuck in this stage" />}
              <Chip size="small" variant="outlined"
                label={`Source: ${SOURCE_LABEL[applicant.source]}${applicant.source_detail ? ` (${applicant.source_detail})` : ''}`} />
              {applicant.next_action && <Chip size="small" variant="outlined" label={`Next: ${applicant.next_action}`} />}
              {applicant.next_action_due && (
                <Chip size="small" color={applicant.next_action_due < today() ? 'error' : 'default'}
                  label={`${applicant.next_action_due < today() ? 'Overdue' : 'Due'} ${applicant.next_action_due}`} />
              )}
            </Stack>

            <TalentPoolPicker applicantId={applicant.id} onError={setError} onChanged={() => reload(applicant.id)} />

            <OtherApplications items={applicant.other_applications}
              onOpen={(id) => setSwitched({ from: openedId, to: id })} />

            <Stack direction="row" spacing={1}>
              {applicant.stage !== 'rejected' && (
                <Button color="error" variant="outlined" onClick={() => setRefusing(true)}>Refuse</Button>
              )}
              {(applicant.archived || applicant.stage === 'rejected') && (
                <Button variant="outlined" onClick={() => run(() => api.restore(applicant.id))}>Restore</Button>
              )}
              {!applicant.archived && (
                <Button variant="outlined" onClick={() => run(() => api.archive(applicant.id))}>Archive</Button>
              )}
              <Button variant="outlined" startIcon={<ContentCopyIcon />} onClick={() => setCopying(true)}>Copy to job</Button>
            </Stack>

            <Stack direction="row" spacing={1}>
              <Button variant="contained" startIcon={<EventIcon />} onClick={() => setBooking(true)}>Schedule interview</Button>
              <Button variant="outlined" startIcon={<EmailIcon />} onClick={() => setComposing({})}>Send email</Button>
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
                  <InterviewItem key={i.id} interview={i} onError={setError}
                    onChanged={(n) => { setNotice(n ?? null); run(async () => {}) }} />
                ))}
              </>
            )}

            <AttachmentList applicantId={applicant.id} items={applicant.attachments} onError={setError}
              onChanged={() => run(async () => {})} />

            <Divider />
            <ApplicantFields key={applicant.id} applicant={applicant} onError={setError}
              onSaved={() => { setNotice({ severity: 'success', text: 'Saved.' }); run(async () => {}) }} />

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
        <RefuseDialog
          applicantId={applicant.id}
          open={refusing}
          onClose={() => setRefusing(false)}
          onRefused={({ emailed, mailError, sendEmail }) => {
            setRefusing(false)
            setNotice(!sendEmail || emailed
              ? { severity: 'success', text: emailed ? 'Applicant refused and emailed.' : 'Applicant refused.' }
              : { severity: 'warning', text: `Applicant refused, but the email failed: ${mailError}` })
            run(async () => {})
          }}
        />
      )}

      {applicant && (
        <CopyToJobDialog applicant={applicant} open={copying} onClose={() => setCopying(false)}
          onCopied={(_copy, jobTitle) => {
            setCopying(false)
            setNotice({ severity: 'success', text: `Copied to ${jobTitle}.` })
            run(async () => {}) // "Also applied to" now lists the copy
          }} />
      )}

      {applicant && composing && (
        <ComposeEmailDialog applicantId={applicant.id} stage={composing.stage} onClose={() => setComposing(null)}
          onSent={({ sent, error }) => {
            setComposing(null)
            setNotice(sent ? { severity: 'success', text: 'Email sent.' } : { severity: 'warning', text: `Email not sent: ${error}` })
            run(async () => {}) // activity log shows the email
          }} />
      )}

      {applicant && (
        <InterviewDialog
          applicantId={applicant.id}
          open={booking}
          onClose={() => setBooking(false)}
          onBooked={({ emailed, mailError, proposed }) => {
            const what = proposed ? 'Times proposed' : 'Interview booked'
            setBooking(false)
            setNotice(emailed
              ? { severity: 'success', text: `${what} and emailed to the candidate.` }
              : { severity: 'warning', text: `${what}, but the email failed: ${mailError}` })
            run(async () => {})
          }}
        />
      )}
    </Drawer>
  )
}
