// One pipeline column with its applicant cards. Cards drag (native HTML5 DnD) onto other columns;
// the stage select in the drawer stays the keyboard-accessible way to move an applicant.
import { useState } from 'react'
import { Avatar, Box, Card, CardActionArea, CardContent, Chip, Paper, Stack, Typography } from '@mui/material'
import { daysInStage, isStuck, STAGE_LABEL, type Applicant, type Stage } from '../api'

type Props = {
  stage: Stage
  items: Applicant[]
  onOpen: (id: number) => void
  onDropApplicant: (id: number, stage: Stage) => void
}

const DRAG_TYPE = 'application/x-applicant-id'

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('').toUpperCase() || '?'
}

export default function StageColumn({ stage, items, onOpen, onDropApplicant }: Props) {
  const [over, setOver] = useState(false)

  return (
    <Paper variant="outlined"
      sx={{ width: 260, flexShrink: 0, p: 1.5, bgcolor: over ? 'action.selected' : 'action.hover', minHeight: 120 }}
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
        <Typography variant="subtitle2" fontWeight={700}>{STAGE_LABEL[stage]}</Typography>
        <Chip size="small" label={items.length} />
      </Stack>
      <Stack spacing={1}>
        {items.map((a) => (
          <Card key={a.id} variant="outlined" draggable sx={{ cursor: 'grab' }}
            onDragStart={(e) => { e.dataTransfer.setData(DRAG_TYPE, String(a.id)); e.dataTransfer.effectAllowed = 'move' }}>
            <CardActionArea onClick={() => onOpen(a.id)}>
              <CardContent sx={{ display: 'flex', gap: 1.5, alignItems: 'center', '&:last-child': { pb: 2 } }}>
                <Avatar sx={{ width: 36, height: 36, fontSize: 14 }}>{initials(a.name)}</Avatar>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle2" noWrap>{a.name}</Typography>
                  <Typography variant="caption" color="text.secondary" noWrap component="div">{a.email}</Typography>
                  {isStuck(a) && <Chip size="small" color="warning" sx={{ mt: 0.5 }} label={`${daysInStage(a)}d in stage`} />}
                </Box>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Stack>
    </Paper>
  )
}
