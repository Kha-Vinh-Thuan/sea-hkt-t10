// Admin-only: edit the candidate email templates (Odoo mail.template). Placeholders: {name}, {job}, {company}.
// Seeded templates (with a key) are the ones the app sends by itself; deleting one falls back to the built-in text.
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  Alert, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem,
  Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { api, STAGE_LABEL, type MailTemplate, type Stage } from '../api'
import { t } from '../i18n'

export default function MailTemplatesPage({ onError }: { onError: (e: Error) => void }) {
  const [templates, setTemplates] = useState<MailTemplate[] | null>(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<'new' | MailTemplate | null>(null)

  const load = useCallback(() => {
    api.mailTemplates().then(setTemplates).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])
  useEffect(load, [load])

  async function remove(tpl: MailTemplate) {
    if (!window.confirm(t('Delete "{name}"?', { name: tpl.name }))) return
    try { await api.deleteMailTemplate(tpl.id); load() } catch (e) { setError((e as Error).message) }
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight={700}>{t('Email templates')}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setEditing('new')}>{t('New template')}</Button>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {t('Placeholders: {name} (applicant), {job} (job title), {company}. A template with a stage is offered when an applicant is moved into that stage.')}
      </Typography>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      {!templates ? <CircularProgress /> : (
        <Card variant="outlined">
          <CardContent sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow><TableCell>{t('Name')}</TableCell><TableCell>{t('Subject')}</TableCell><TableCell>{t('Stage')}</TableCell><TableCell /></TableRow>
              </TableHead>
              <TableBody>
                {templates.map((tpl) => (
                  <TableRow key={tpl.id}>
                    <TableCell>{tpl.name}{tpl.key && <Chip size="small" variant="outlined" label={t('built-in')} sx={{ ml: 1 }} />}</TableCell>
                    <TableCell>{tpl.subject}</TableCell>
                    <TableCell>{tpl.stage ? t(STAGE_LABEL[tpl.stage]) : '—'}</TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Button size="small" onClick={() => setEditing(tpl)}>{t('Edit')}</Button>
                      <Button size="small" color="error" onClick={() => remove(tpl)}>{t('Delete')}</Button>
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
        <DialogTitle>{template ? t('Edit {name}', { name: template.name }) : t('New template')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField name="name" label={t('Name')} defaultValue={template?.name} required autoFocus />
            <TextField name="stage" label={t('Offer when moved to stage')} select defaultValue={template?.stage ?? ''}>
              <MenuItem value="">{t('None')}</MenuItem>
              {Object.entries(STAGE_LABEL).map(([value, label]) => <MenuItem key={value} value={value}>{t(label)}</MenuItem>)}
            </TextField>
            <TextField name="subject" label={t('Subject')} defaultValue={template?.subject} required />
            <TextField name="body" label={t('Body')} defaultValue={template?.body} multiline minRows={8} />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t('Cancel')}</Button>
          <Button type="submit" variant="contained" loading={busy}>{template ? t('Save') : t('Create')}</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
