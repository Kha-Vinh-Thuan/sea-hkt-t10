// One interview in the applicant drawer: time, interviewer, status, scorecard, and the actions allowed right now.
import { useState } from 'react'
import { Box, Button, Chip, Link, Rating, Stack, Typography } from '@mui/material'
import {
  api, CANDIDATE_RESPONSE_LABEL, formatWhen, INTERVIEW_STATUS_COLOR, INTERVIEW_STATUS_LABEL, RECOMMENDATION_LABEL, type Interview,
} from '../api'
import { t } from '../i18n'
import FeedbackDialog from './FeedbackDialog'
import InterviewDialog from './InterviewDialog'

type Notice = { severity: 'success' | 'warning'; text: string }

type Props = { interview: Interview; onChanged: (notice?: Notice) => void; onError: (message: string) => void }

export default function InterviewItem({ interview: i, onChanged, onError }: Props) {
  const [dialog, setDialog] = useState<'reschedule' | 'feedback' | null>(null)
  const started = new Date(i.start).getTime() <= Date.now()

  function mailNotice(action: string, emailed: boolean, mailError: string | null): Notice {
    return emailed
      ? { severity: 'success', text: t('Interview {action}; email sent.', { action: t(action) }) }
      : { severity: 'warning', text: t('Interview {action}, but the email failed: {error}', { action: t(action), error: mailError ?? '' }) }
  }

  async function cancel() {
    if (!window.confirm(t('Cancel the interview on {when}? Both attendees get a cancellation email.', { when: formatWhen(i.start) }))) return
    try {
      const result = await api.cancelInterview(i.id)
      onChanged(mailNotice('cancelled', result.emailed, result.mail_error))
    } catch (e) {
      onError((e as Error).message)
    }
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Typography variant="body2" fontWeight={600}
          sx={{ textDecoration: i.status === 'cancelled' ? 'line-through' : undefined }}>
          {formatWhen(i.start)}
        </Typography>
        <Chip size="small" label={t(INTERVIEW_STATUS_LABEL[i.status])} color={INTERVIEW_STATUS_COLOR[i.status]} />
      </Stack>
      <Typography variant="caption" color="text.secondary" component="div">
        {i.interviewer_name || i.interviewer_email}{i.location && i.location !== i.meet_url && ` · ${i.location}`}
      </Typography>
      {(i.meet_url || (i.status === 'scheduled' && i.candidate_response !== 'none')) && (
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          {i.status === 'scheduled' && i.candidate_response !== 'none' && (
            <Chip size="small" variant="outlined" label={t(CANDIDATE_RESPONSE_LABEL[i.candidate_response])}
              color={i.candidate_response === 'accepted' ? 'success' : 'error'} />
          )}
          {i.meet_url && <Link variant="caption" href={i.meet_url} target="_blank" rel="noreferrer">Google Meet</Link>}
        </Stack>
      )}
      {(i.score || i.recommendation) && (
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          {i.score && <Rating size="small" value={i.score} readOnly />}
          {i.recommendation && <Typography variant="caption">{t(RECOMMENDATION_LABEL[i.recommendation])}</Typography>}
        </Stack>
      )}
      {i.feedback && <Typography variant="caption" component="div" sx={{ whiteSpace: 'pre-line' }}>{i.feedback}</Typography>}

      <Stack direction="row" spacing={1}>
        {i.status === 'scheduled' && (
          <>
            <Button size="small" onClick={() => setDialog('reschedule')}>{t('Reschedule')}</Button>
            <Button size="small" color="error" onClick={cancel}>{t('Cancel')}</Button>
          </>
        )}
        {started && i.status !== 'cancelled' && (
          <Button size="small" onClick={() => setDialog('feedback')}>{t('Feedback')}</Button>
        )}
      </Stack>

      <InterviewDialog
        applicantId={i.applicant_id}
        interview={i}
        open={dialog === 'reschedule'}
        onClose={() => setDialog(null)}
        onBooked={({ emailed, mailError }) => { setDialog(null); onChanged(mailNotice('rescheduled', emailed, mailError)) }}
      />
      {dialog === 'feedback' && (
        <FeedbackDialog interview={i} open onClose={() => setDialog(null)}
          onSaved={() => { setDialog(null); onChanged() }} />
      )}
    </Box>
  )
}
