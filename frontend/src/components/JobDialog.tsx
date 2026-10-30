// Dialog to create a job position, or edit one when `job` is given.
import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Autocomplete, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Switch, TextField,
} from '@mui/material'
import { api, EMPLOYMENT_LABEL, type EmploymentType, type Job, type UserBrief } from '../api'

// Parent passes a fresh `key` per job, so the uncontrolled inputs pick up the new defaults.
type Props = { open: boolean; job?: Job; onClose: () => void; onSaved: (job: Job) => void }

export default function JobDialog({ open, job, onClose, onSaved }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [users, setUsers] = useState<UserBrief[]>([])
  const [interviewerIds, setInterviewerIds] = useState<number[]>(job?.interviewer_ids ?? [])
  const [tags, setTags] = useState<string[]>(job?.tags ?? [])

  useEffect(() => {
    if (open) api.users().then(setUsers).catch((e: Error) => setError(e.message))
  }, [open])
  const userLabel = (id: number) => { const u = users.find((x) => x.id === id); return u ? u.name || u.email : `#${id}` }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    const numberOrNull = (key: string) => (text(key) ? Number(text(key)) : null)
    const input = {
      title: text('title'),
      department: text('department'),
      location: text('location'),
      description: text('description'),
      requirements: text('requirements'),
      interview_duration_minutes: Number(text('interview_duration_minutes')),
      openings: Number(text('openings')),
      is_open: f.get('is_open') === 'on',
      opens_on: text('opens_on') || null,
      closes_on: text('closes_on') || null,
      employment_type: text('employment_type') as EmploymentType,
      is_remote: f.get('is_remote') === 'on',
      salary_min: numberOrNull('salary_min'),
      salary_max: numberOrNull('salary_max'),
      expected_degree: text('expected_degree'),
      interviewer_ids: interviewerIds,
      recruiter_id: numberOrNull('recruiter_id'),
      manager_id: numberOrNull('manager_id'),
      tags,
    }
    setBusy(true)
    setError('')
    try {
      onSaved(await (job ? api.updateJob(job.id, input) : api.createJob(input)))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const dateInput = { inputLabel: { shrink: true } }
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <form onSubmit={submit}>
        <DialogTitle>{job ? 'Edit job position' : 'New job position'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="title" label="Title" required autoFocus defaultValue={job?.title} />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="department" label="Department" fullWidth defaultValue={job?.department} />
              <TextField name="location" label="Location" fullWidth defaultValue={job?.location} />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'center' } }}>
              <TextField name="employment_type" label="Employment type" select fullWidth
                defaultValue={job?.employment_type ?? 'full_time'}>
                {Object.entries(EMPLOYMENT_LABEL).map(([value, label]) => (
                  <MenuItem key={value} value={value}>{label}</MenuItem>
                ))}
              </TextField>
              <FormControlLabel control={<Switch name="is_remote" defaultChecked={job?.is_remote} />} label="Remote"
                sx={{ flexShrink: 0 }} />
            </Stack>
            <TextField name="description" label="Description" multiline minRows={3} defaultValue={job?.description} />
            <TextField name="requirements" label="Requirements" multiline minRows={3} placeholder="One per line"
              defaultValue={job?.requirements} />
            <TextField name="expected_degree" label="Expected degree" placeholder="e.g. Bachelor in Computer Science"
              defaultValue={job?.expected_degree} />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="salary_min" label="Salary from (VND / month)" type="number" fullWidth
                defaultValue={job?.salary_min ?? ''} slotProps={{ htmlInput: { min: 0, step: 500000 } }} />
              <TextField name="salary_max" label="Salary to (VND / month)" type="number" fullWidth
                defaultValue={job?.salary_max ?? ''} slotProps={{ htmlInput: { min: 0, step: 500000 } }} />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="opens_on" label="Opens on" type="date" fullWidth
                defaultValue={job?.opens_on ?? ''} slotProps={dateInput} />
              <TextField name="closes_on" label="Closes on" type="date" fullWidth
                defaultValue={job?.closes_on ?? ''} slotProps={dateInput} />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField name="interview_duration_minutes" label="Interview length (min)" type="number"
                defaultValue={job?.interview_duration_minutes ?? 45} required fullWidth slotProps={{ htmlInput: { min: 5 } }} />
              <TextField name="openings" label="Openings" type="number" defaultValue={job?.openings ?? 1} required fullWidth
                slotProps={{ htmlInput: { min: 0 } }} />
            </Stack>
            <Autocomplete
              multiple freeSolo options={[]} value={tags}
              onChange={(_e, value) => setTags(value as string[])}
              renderValue={(value, getItemProps) =>
                value.map((tag, index) => <Chip size="small" label={tag} {...getItemProps({ index })} key={tag} />)}
              renderInput={(params) => <TextField {...params} label="Tags" placeholder="Type and press Enter" />}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              {(['recruiter_id', 'manager_id'] as const).map((key) => (
                <TextField key={key} name={key} label={key === 'recruiter_id' ? 'Recruiter' : 'Hiring manager'} select
                  fullWidth defaultValue={job?.[key] ?? ''}>
                  <MenuItem value="">None</MenuItem>
                  {users.map((u) => <MenuItem key={u.id} value={u.id}>{u.name || u.email}</MenuItem>)}
                </TextField>
              ))}
            </Stack>
            <TextField label="Interviewers" select fullWidth value={interviewerIds}
              helperText="Offered first when booking an interview for this job"
              onChange={(e) => setInterviewerIds(e.target.value as unknown as number[])}
              slotProps={{ select: { multiple: true, renderValue: (ids) => (ids as number[]).map(userLabel).join(', ') } }}>
              {users.map((u) => <MenuItem key={u.id} value={u.id}>{u.name || u.email} ({u.email})</MenuItem>)}
            </TextField>
            <FormControlLabel control={<Switch name="is_open" defaultChecked={job?.is_open ?? true} />}
              label="Published on careers site" />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>{job ? 'Save' : 'Create'}</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
