// One pipeline column with its applicant cards. Cards drag (native HTML5 DnD) onto other columns;
// the stage select in the drawer stays the keyboard-accessible way to move an applicant.
import { useState } from 'react'
import { Avatar, Box, Card, CardActionArea, CardContent, Chip, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { daysInStage, isStuck, STAGE_LABEL, type Applicant, type Stage } from '../api'
import { t } from '../i18n'

type Props = {
  stage: Stage
  items: Applicant[]
  onOpen: (id: number) => void
  onDropApplicant: (id: number, stage: Stage) => void
}

const DRAG_TYPE = 'application/x-applicant-id'
// One accent per stage: column top bar, count badge and card avatars.
const STAGE_COLOR: Record<Stage, string> = {
  new: '#64748b', screening: '#0ea5e9', interview: '#8b5cf6', offer: '#f59e0b', hired: '#10b981', rejected: '#ef4444',
}

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('').toUpperCase() || '?'
}

// Interview column only: red = no interview booked yet (needs scheduling), green = booked or done.
function InterviewDot({ booked }: { booked: boolean }) {
  const label = booked ? t('Interview booked') : t('No interview booked yet')
  return (
    <Tooltip title={label}>
      <Box role="img" aria-label={label}
        sx={{ width: 10, height: 10, borderRadius: '50%', flexShrink: 0, bgcolor: booked ? 'success.main' : 'error.main' }} />
    </Tooltip>
  )
}

export default function StageColumn({ stage, items, onOpen, onDropApplicant }: Props) {
  const [over, setOver] = useState(false)

  return (
    <Paper variant="outlined"
      sx={{ width: 272, flexShrink: 0, p: 1.5, minHeight: 160, border: 0, borderTop: 4, borderColor: STAGE_COLOR[stage],
        bgcolor: over ? 'action.selected' : 'action.hover', transition: 'background-color .15s' }}
      // Only react to our own cards, not to files or text dragged in from elsewhere.
      onDragOver={(e) => { if (e.dataTransfer.types.includes(DRAG_TYPE)) { e.preventDefault(); setOver(true) } }}
      onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false) }}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        const id = Number(e.dataTransfer.getData(DRAG_TYPE))
        if (id) onDropApplicant(id, stage)
      }}>
      <Stack direction="row" sx={{ mb: 1.5, alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="subtitle2" fontWeight={700}>{t(STAGE_LABEL[stage])}</Typography>
        <Chip size="small" label={items.length} sx={{ bgcolor: STAGE_COLOR[stage], color: '#fff' }} />
      </Stack>
      <Stack spacing={1}>
        {items.map((a) => (
          <Card key={a.id} elevation={0} draggable
            sx={{ cursor: 'grab', boxShadow: '0 1px 3px rgba(15,23,42,.08)', transition: 'box-shadow .15s, transform .15s',
              '&:hover': { boxShadow: '0 6px 16px rgba(15,23,42,.12)', transform: 'translateY(-1px)' } }}
            onDragStart={(e) => { e.dataTransfer.setData(DRAG_TYPE, String(a.id)); e.dataTransfer.effectAllowed = 'move' }}>
            <CardActionArea onClick={() => onOpen(a.id)}>
              <CardContent sx={{ display: 'flex', gap: 1.5, alignItems: 'center', '&:last-child': { pb: 2 } }}>
                <Avatar sx={{ width: 36, height: 36, fontSize: 14, fontWeight: 700, bgcolor: STAGE_COLOR[stage] }}>{initials(a.name)}</Avatar>
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography variant="subtitle2" noWrap>{a.name}</Typography>
                  <Typography variant="caption" color="text.secondary" noWrap component="div">{a.email}</Typography>
                  {isStuck(a) && <Chip size="small" color="warning" sx={{ mt: 0.5 }} label={t('{days}d in stage', { days: daysInStage(a) })} />}
                </Box>
                {stage === 'interview' && <InterviewDot booked={Boolean(a.interview_count)} />}
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
        {!items.length && (
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', py: 3, border: 1,
            borderStyle: 'dashed', borderColor: 'divider', borderRadius: 3 }}>
            {t('Drop applicants here')}
          </Typography>
        )}
      </Stack>
    </Paper>
  )
}
