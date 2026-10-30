// Dialog to create a job position.
import { useState, type FormEvent } from 'react'
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Stack, Switch, TextField,
} from '@mui/material'
import { api, type Job } from '../api'

type Props = { open: boolean; onClose: () => void; onCreated: (job: Job) => void }

export default function JobDialog({ open, onClose, onCreated }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    setBusy(true)
    setError('')
    try {
      onCreated(await api.createJob({
        title: text('title'),
        department: text('department'),
        location: text('location'),
        description: text('description'),
        requirements: text('requirements'),
        interview_duration_minutes: Number(text('interview_duration_minutes')),
        openings: Number(text('openings')),
        is_open: f.get('is_open') === 'on',
      }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <form onSubmit={submit}>
        <DialogTitle>New job position</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="title" label="Title" required autoFocus />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="department" label="Department" fullWidth />
              <TextField name="location" label="Location" fullWidth />
            </Stack>
            <TextField name="description" label="Description" multiline minRows={3} />
            <TextField name="requirements" label="Requirements" multiline minRows={3} placeholder="One per line" />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="interview_duration_minutes" label="Interview length (min)" type="number"
                defaultValue={45} required fullWidth slotProps={{ htmlInput: { min: 5 } }} />
              <TextField name="openings" label="Openings" type="number" defaultValue={1} required fullWidth
                slotProps={{ htmlInput: { min: 0 } }} />
            </Stack>
            <FormControlLabel control={<Switch name="is_open" defaultChecked />} label="Published on careers site" />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>Create</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
