// Recruiter-editable fields of one applicant (stars, tags, notes, LinkedIn, degree, start date, salaries) + Save.
import { useState } from 'react'
import { Autocomplete, Button, Chip, Rating, Stack, TextField, Typography } from '@mui/material'
import { api, type ApplicantDetail, type ApplicantUpdate } from '../api'

type Props = { applicant: ApplicantDetail; onSaved: () => void; onError: (message: string) => void }

const toForm = (a: ApplicantDetail): ApplicantUpdate => ({
  notes: a.notes, priority: a.priority, tags: a.tags, linkedin: a.linkedin, available_from: a.available_from,
  degree: a.degree, salary_expected: a.salary_expected, salary_proposed: a.salary_proposed,
})

// Empty number inputs mean "not set" (null), not 0.
const toNumber = (value: string) => (value === '' ? null : Number(value))

// The drawer remounts this with key={applicant.id}, so the form resets when another applicant is opened.
export default function ApplicantFields({ applicant, onSaved, onError }: Props) {
  const [form, setForm] = useState<ApplicantUpdate>(() => toForm(applicant))
  const [busy, setBusy] = useState(false)
  const set = (patch: Partial<ApplicantUpdate>) => setForm((f) => ({ ...f, ...patch }))

  async function save() {
    setBusy(true)
    try {
      await api.updateApplicant(applicant.id, form)
      onSaved()
    } catch (e) {
      onError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">Priority</Typography>
        <Rating max={3} value={form.priority} onChange={(_e, v) => set({ priority: v ?? 0 })} />
      </Stack>
      <Autocomplete
        multiple freeSolo options={[]} value={form.tags}
        onChange={(_e, tags) => set({ tags: tags as string[] })}
        renderValue={(tags, getItemProps) =>
          tags.map((tag, index) => <Chip size="small" label={tag} {...getItemProps({ index })} key={tag} />)}
        renderInput={(params) => <TextField {...params} label="Tags" placeholder="Type and press Enter" />}
      />
      <TextField label="Recruiter notes" multiline minRows={3} value={form.notes}
        onChange={(e) => set({ notes: e.target.value })} />
      <TextField label="LinkedIn" type="url" value={form.linkedin} placeholder="https://"
        onChange={(e) => set({ linkedin: e.target.value })} />
      <Stack direction="row" spacing={1}>
        <TextField label="Degree" fullWidth value={form.degree} onChange={(e) => set({ degree: e.target.value })} />
        <TextField label="Available from" type="date" fullWidth value={form.available_from ?? ''}
          slotProps={{ inputLabel: { shrink: true } }}
          onChange={(e) => set({ available_from: e.target.value || null })} />
      </Stack>
      <Stack direction="row" spacing={1}>
        <TextField label="Expected salary" type="number" fullWidth value={form.salary_expected ?? ''}
          slotProps={{ htmlInput: { min: 0 } }} onChange={(e) => set({ salary_expected: toNumber(e.target.value) })} />
        <TextField label="Proposed salary" type="number" fullWidth value={form.salary_proposed ?? ''}
          slotProps={{ htmlInput: { min: 0 } }} onChange={(e) => set({ salary_proposed: toNumber(e.target.value) })} />
      </Stack>
      <Button variant="outlined" onClick={save} disabled={busy} sx={{ alignSelf: 'flex-start' }}>
        {busy ? 'Saving…' : 'Save'}
      </Button>
    </Stack>
  )
}
