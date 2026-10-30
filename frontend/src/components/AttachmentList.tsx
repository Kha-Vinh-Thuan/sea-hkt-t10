// "Attachments" in the applicant drawer: files other than the CV (Odoo attachment_ids). Upload, download, delete.
import { Box, Button, IconButton, Link, Stack, Typography } from '@mui/material'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { api, type Attachment } from '../api'

type Props = { applicantId: number; items: Attachment[]; onChanged: () => void; onError: (message: string) => void }

// Same list the backend checks; the server is the real gate.
const ACCEPT = '.pdf,.docx,.txt,.png,.jpg,.jpeg'

export default function AttachmentList({ applicantId, items, onChanged, onError }: Props) {
  const run = (action: () => Promise<unknown>) => action().then(onChanged).catch((e: Error) => onError(e.message))

  return (
    <Box>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="subtitle2" fontWeight={700}>Attachments</Typography>
        <Button size="small" component="label" startIcon={<UploadFileIcon />}>
          Upload
          <input hidden type="file" accept={ACCEPT} onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = '' // lets the same file be picked again after an error
            if (file) run(() => api.uploadAttachment(applicantId, file))
          }} />
        </Button>
      </Stack>
      {items.length === 0 && <Typography variant="body2" color="text.secondary">PDF, DOCX, TXT, PNG or JPG, up to 5 MB.</Typography>}
      {items.map((a) => (
        <Stack key={a.id} direction="row" sx={{ alignItems: 'center' }}>
          <Link component="button" variant="body2" sx={{ flex: 1, textAlign: 'left' }}
            onClick={() => api.downloadAttachment(a).catch((e: Error) => onError(e.message))}>
            {a.filename}
          </Link>
          <Typography variant="caption" color="text.secondary" sx={{ mx: 1 }}>{Math.ceil(a.size / 1024)} KB</Typography>
          <IconButton size="small" aria-label={`Delete ${a.filename}`}
            onClick={() => { if (confirm(`Delete ${a.filename}?`)) run(() => api.deleteAttachment(applicantId, a.id)) }}>
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Stack>
      ))}
    </Box>
  )
}
