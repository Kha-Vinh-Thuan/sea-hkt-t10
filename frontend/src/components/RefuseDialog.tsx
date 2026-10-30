// Refuse an applicant: pick a reason (always recorded) and optionally email the candidate.
import { useEffect, useState } from 'react'
import {
  Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField,
} from '@mui/material'
import { api, type RefuseReason, type RefuseReasonOption } from '../api'

type Props = {
  applicantId: number
  open: boolean
  onClose: () => void
  onRefused: (notice: { emailed: boolean; mailError: string | null; sendEmail: boolean }) => void
}

export default function RefuseDialog({ applicantId, open, onClose, onRefused }: Props) {
  const [reason, setReason] = useState<RefuseReason>('does_not_fit')
  const [sendEmail, setSendEmail] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [reasons, setReasons] = useState<RefuseReasonOption[]>([])

  // Fetched on first open: the backend owns the reason list and its labels.
  useEffect(() => {
    if (open && !reasons.length) api.refuseReasons().then(setReasons).catch((e: Error) => setError(e.message))
  }, [open, reasons.length])

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const result = await api.refuse(applicantId, reason, sendEmail)
      onRefused({ emailed: result.emailed, mailError: result.mail_error, sendEmail })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Refuse applicant</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select label="Reason" value={reason} onChange={(e) => setReason(e.target.value as RefuseReason)}>
            {/* Keeps the default selectable before the list arrives, so MUI doesn't warn about an unknown value. */}
            {(reasons.length ? reasons : [{ value: reason, label: '…' }]).map((r) => (
              <MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>
            ))}
          </TextField>
          <FormControlLabel label="Send refusal email to the candidate"
            control={<Checkbox checked={sendEmail} onChange={(e) => setSendEmail(e.target.checked)} />} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button color="error" variant="contained" onClick={submit} disabled={busy || !reasons.length}>Refuse</Button>
      </DialogActions>
    </Dialog>
  )
}
