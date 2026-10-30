// Admin-only: every account with its role and status; create, edit and reset passwords through UserDialog.
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, CardContent, Chip, CircularProgress, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { api, ROLE_LABEL, type User } from '../api'
import UserDialog from '../components/UserDialog'
import { t } from '../i18n'

type Props = { currentUserId: number; onError: (e: Error) => void }

export default function UsersPage({ currentUserId, onError }: Props) {
  const [users, setUsers] = useState<User[] | null>(null)
  const [error, setError] = useState('')
  const [dialog, setDialog] = useState<'new' | User | null>(null)

  const load = useCallback(() => {
    api.adminUsers().then(setUsers).catch((e: Error) => { setError(e.message); onError(e) })
  }, [onError])
  useEffect(load, [load])

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight={700}>{t('Users')}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog('new')}>{t('New user')}</Button>
      </Stack>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      {!users ? <CircularProgress /> : (
        <Card variant="outlined">
          <CardContent sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('Name')}</TableCell>
                  <TableCell>{t('Email')}</TableCell>
                  <TableCell>{t('Role')}</TableCell>
                  <TableCell>{t('Status')}</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>{u.name || '—'}{u.id === currentUserId && ` (${t('you')})`}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>{t(ROLE_LABEL[u.role])}</TableCell>
                    <TableCell>
                      <Chip size="small" label={u.is_active ? t('Active') : t('Inactive')} color={u.is_active ? 'success' : 'default'} />
                    </TableCell>
                    <TableCell align="right"><Button size="small" onClick={() => setDialog(u)}>{t('Edit')}</Button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      {dialog && (
        <UserDialog user={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)}
          onSaved={() => { setDialog(null); load() }} />
      )}
    </Stack>
  )
}
