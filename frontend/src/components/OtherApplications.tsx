// "Also applied to" in the applicant drawer: the same person's applications to other jobs (Odoo application_count).
import { Box, Link, Typography } from '@mui/material'
import { STAGE_LABEL, type OtherApplication } from '../api'

type Props = { items: OtherApplication[]; onOpen: (applicantId: number) => void }

export default function OtherApplications({ items, onOpen }: Props) {
  if (items.length === 0) return null
  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={700}>Also applied to</Typography>
      {items.map((o) => (
        <Typography key={o.id} variant="body2">
          <Link component="button" onClick={() => onOpen(o.id)}>{o.job_title}</Link>
          {` · ${STAGE_LABEL[o.stage]}${o.archived ? ' (archived)' : ''} · ${new Date(o.created_at).toLocaleDateString()}`}
        </Typography>
      ))}
    </Box>
  )
}
