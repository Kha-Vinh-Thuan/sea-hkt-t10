// Applicant activity as a timeline, newest first. The server writes English text; the two common shapes are made
// friendlier here: "Stage: a → b" shows translated stage names, "Email sent: subject\n\nbody" shows the subject and
// hides the body behind a click.
import { useState } from 'react'
import { Box, Link, Stack, Typography } from '@mui/material'
import { STAGE_LABEL, type Activity, type Stage } from '../api'
import { locale, t } from '../i18n'

const stageName = (s: string) => (s in STAGE_LABEL ? t(STAGE_LABEL[s as Stage]) : s)

function Message({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  const stage = text.match(/^Stage: (\w+) → (\w+)$/)
  if (stage) return <Typography variant="body2">{t('Stage')}: {stageName(stage[1])} → <b>{stageName(stage[2])}</b></Typography>
  const [head, ...rest] = text.split('\n\n')
  const body = rest.join('\n\n')
  return (
    <Box>
      <Typography variant="body2">{head}</Typography>
      {body && (
        <>
          <Link component="button" variant="caption" onClick={() => setOpen(!open)}>
            {open ? t('Hide email') : t('Show email')}
          </Link>
          {open && (
            <Typography variant="body2" color="text.secondary"
              sx={{ whiteSpace: 'pre-line', mt: 0.5, p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}>
              {body}
            </Typography>
          )}
        </>
      )}
    </Box>
  )
}

export default function ActivityLog({ items }: { items: Activity[] }) {
  return (
    <Stack spacing={1.5}>
      {[...items].reverse().map((item) => (
        <Stack key={item.id} direction="row" spacing={1.5}>
          <Box sx={{ width: 8, height: 8, mt: 0.75, borderRadius: '50%', bgcolor: 'primary.main', flexShrink: 0 }} />
          <Box sx={{ minWidth: 0 }}>
            <Message text={item.message} />
            <Typography variant="caption" color="text.secondary">
              {new Date(item.created_at).toLocaleString(locale(), { dateStyle: 'medium', timeStyle: 'short' })}
            </Typography>
          </Box>
        </Stack>
      ))}
    </Stack>
  )
}
