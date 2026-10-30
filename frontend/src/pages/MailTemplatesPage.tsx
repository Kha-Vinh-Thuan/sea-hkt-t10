// Admin-only: edit the candidate email templates (Odoo mail.template). Placeholders: {name}, {job}, {company}.
// Seeded templates (with a key) are the ones the app sends by itself; deleting one falls back to the built-in text.
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem,
  Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { api, STAGE_LABEL, type MailTemplate, type Stage } from '../api'

export default function MailTemplatesPage({ onError }: { onError: (e: Error) => void }) {
  const [templates, setTemplates] = useState<MailTemplate[] | null>(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<'new' | MailTemplate | null>(null)

  const load = useCallback(() => {
    api.mailTemplates().then(setTemplates).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])
  useEffect(load, [load])

  async function remove(t: MailTemplate) {
    if (!window.confirm(`Delete "${t.name}"?`)) return
    try { await api.deleteMailTemplate(t.id); load() } catch (e) { setError((e as Error).message) }
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight={700}>Email templates</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setEditing('new')}>New template</Button>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        Placeholders: {'{name}'} (applicant), {'{job}'} (job title), {'{company}'}. A template with a stage is offered
        when an applicant is moved into that stage.
      </Typography>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      {!templates ? <CircularProgress /> : (
        <Card variant="outlined">
          <CardContent sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow><TableCell>Name</TableCell><TableCell>Subject</TableCell><TableCell>Stage</TableCell><TableCell /></TableRow>
              </TableHead>
              <TableBody>
                {templates.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>{t.name}{t.key && <Chip size="small" variant="outlined" label="built-in" sx={{ ml: 1 }} />}</TableCell>
                    <TableCell>{t.subject}</TableCell>
                    <TableCell>{t.stage ? STAGE_LABEL[t.stage] : '—'}</TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Button size="small" onClick={() => setEditing(t)}>Edit</Button>
                      <Button size="small" color="error" onClick={() => remove(t)}>Delete</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      {editing && (
        <TemplateDialog template={editing === 'new' ? undefined : editing} onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load() }} />
      )}
    </Stack>
  )
}

function TemplateDialog({ template, onClose, onSaved }: { template?: MailTemplate; onClose: () => void; onSaved: () => void }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '')
    const data = { name: text('name').trim(), subject: text('subject'), body: text('body'), stage: (text('stage') || null) as Stage | null }
    setBusy(true)
    setError('')
    try {
      await (template ? api.updateMailTemplate(template.id, data) : api.createMailTemplate(data))
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <form onSubmit={submit}>
        <DialogTitle>{template ? `Edit ${template.name}` : 'New template'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="name" label="Name" defaultValue={template?.name} required autoFocus />
            <TextField name="stage" label="Offer when moved to stage" select defaultValue={template?.stage ?? ''}>
              <MenuItem value="">None</MenuItem>
              {Object.entries(STAGE_LABEL).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
            </TextField>
            <TextField name="subject" label="Subject" defaultValue={template?.subject} required />
            <TextField name="body" label="Body" defaultValue={template?.body} multiline minRows={8} />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>{template ? 'Save' : 'Create'}</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
