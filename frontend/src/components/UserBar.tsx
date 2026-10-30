// Thin strip above every staff screen: who is signed in, admin's switch to the Users page, sign out.
// Kept outside BoardPage so the board's own header stays untouched.
import { Button, Chip, Stack, Typography } from '@mui/material'
import LogoutIcon from '@mui/icons-material/Logout'
import { ROLE_LABEL, type UserBrief } from '../api'

type Props = {
  user: UserBrief
  page: 'board' | 'users'
  onPage: (page: 'board' | 'users') => void
  onSignOut: () => void
}

export default function UserBar({ user, page, onPage, onSignOut }: Props) {
  return (
    <Stack direction="row" spacing={1} sx={{ px: 2, py: 0.5, alignItems: 'center', justifyContent: 'flex-end',
      bgcolor: 'action.hover', borderBottom: 1, borderColor: 'divider', flexWrap: 'wrap' }}>
      {user.role === 'admin' && (
        <Button size="small" onClick={() => onPage(page === 'users' ? 'board' : 'users')}>
          {page === 'users' ? 'Recruitment' : 'Users'}
        </Button>
      )}
      <Typography variant="body2" fontWeight={600}>{user.name || user.email}</Typography>
      <Chip size="small" label={ROLE_LABEL[user.role]} />
      <Button size="small" startIcon={<LogoutIcon />} onClick={onSignOut}>Sign out</Button>
    </Stack>
  )
}
