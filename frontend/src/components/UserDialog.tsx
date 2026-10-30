// Create a user (email, name, role, initial password) or edit one (name, role, active, optional new password).
// The server refuses demoting / deactivating yourself or the last admin; its message shows here.
import { useState, type FormEvent } from 'react'
import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Switch, TextField,
} from '@mui/material'
import { api, ROLE_LABEL, type Role, type User } from '../api'
import { t } from '../i18n'

type Props = { user?: User; onClose: () => void; onSaved: () => void }

export default function UserDialog({ user, onClose, onSaved }: Props) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const text = (key: string) => String(f.get(key) ?? '').trim()
    setBusy(true)
    setError('')
    try {
      const role = text('role') as Role
      if (user) {
        await api.updateUser(user.id, { name: text('name'), role, is_active: f.get('is_active') === 'on' })
        if (text('password')) await api.resetPassword(user.id, text('password'))
      } else {
        await api.createUser({ email: text('email'), name: text('name'), role, password: text('password') })
      }
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={submit}>
        <DialogTitle>{user ? t('Edit {email}', { email: user.email }) : t('New user')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {!user && <TextField name="email" label={t('Email')} type="email" required autoFocus />}
            <TextField name="name" label={t('Name')} defaultValue={user?.name} />
            <TextField name="role" label={t('Role')} select defaultValue={user?.role ?? 'recruiter'}>
              {Object.entries(ROLE_LABEL).map(([value, label]) => <MenuItem key={value} value={value}>{t(label)}</MenuItem>)}
            </TextField>
            {user && <FormControlLabel control={<Switch name="is_active" defaultChecked={user.is_active} />} label={t('Active')} />}
            <TextField name="password" label={user ? t('New password (leave empty to keep)') : t('Initial password')}
              type="password" required={!user} autoComplete="new-password" slotProps={{ htmlInput: { minLength: 8 } }} />
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t('Cancel')}</Button>
          <Button type="submit" variant="contained" loading={busy}>{user ? t('Save') : t('Create')}</Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
