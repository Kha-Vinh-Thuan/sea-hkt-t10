// The one top bar of every staff screen: main sections on the left (Pipeline, Interviews, "More" for the rarely
// used ones), the account menu on the right (admin pages, Google Calendar connect / disconnect, sign out).
// Interviewers only have their interviews, so they get no section links.
import { useState, type MouseEvent } from 'react'
import {
  AppBar, Avatar, Box, Button, Chip, Divider, IconButton, ListItemIcon, ListItemText, Menu, MenuItem, Toolbar, Tooltip, Typography,
  useColorScheme,
} from '@mui/material'
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined'
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined'
import EventIcon from '@mui/icons-material/Event'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import LogoutIcon from '@mui/icons-material/Logout'
import MailOutlineIcon from '@mui/icons-material/MailOutline'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import PeopleOutlineIcon from '@mui/icons-material/PeopleOutline'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline'
import { api, ROLE_LABEL, type UserBrief } from '../api'
import { setLang, t, useLang } from '../i18n'

export type StaffPage = 'pipeline' | 'interviews' | 'reports' | 'pools' | 'users' | 'templates'
const MAIN: [StaffPage, string][] = [['pipeline', 'Pipeline'], ['interviews', 'Interviews']]
const MORE: [StaffPage, string][] = [['reports', 'Reports'], ['pools', 'Talent pools']]

type Props = {
  user: UserBrief & { google_connected?: boolean }
  page: StaffPage
  onPage: (page: StaffPage) => void
  onSignOut: () => void
  onGoogleChanged: () => void
  onError: (e: Error) => void
}

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('').toUpperCase() || '?'
}

// A section link: the current one is a tinted pill in the primary colour.
function NavButton({ active, ...props }: { active: boolean } & React.ComponentProps<typeof Button>) {
  return (
    <Button color={active ? 'primary' : 'inherit'} aria-current={active ? 'page' : undefined} {...props}
      sx={{ px: 2, mx: 0.25, fontWeight: active ? 700 : 500, color: active ? 'primary.main' : 'text.secondary',
        bgcolor: active ? 'action.selected' : 'transparent' }} />
  )
}

export default function NavBar({ user, page, onPage, onSignOut, onGoogleChanged, onError }: Props) {
  const [moreAt, setMoreAt] = useState<HTMLElement | null>(null)
  const [accountAt, setAccountAt] = useState<HTMLElement | null>(null)
  const staff = user.role !== 'interviewer'
  const lang = useLang()
  const { mode, systemMode, setMode } = useColorScheme()
  const dark = (mode === 'system' ? systemMode : mode) === 'dark'
  const inMore = MORE.find(([p]) => p === page)

  function go(next: StaffPage) {
    setMoreAt(null)
    setAccountAt(null)
    onPage(next)
  }

  // Full-page redirect to Google's consent screen; Google sends the browser back to /?google=connected.
  function connect() {
    api.googleConnectUrl().then(({ url }) => { window.location.href = url }).catch(onError)
  }

  function disconnect() {
    setAccountAt(null)
    if (!window.confirm(t('Disconnect Google Calendar? New interviews will no longer be added to it.'))) return
    api.googleDisconnect().then(onGoogleChanged).catch(onError)
  }

  return (
    <AppBar position="sticky" elevation={0} color="inherit"
      sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
      <Toolbar sx={{ gap: 0.5, minHeight: 64 }}>
        <Avatar variant="rounded" sx={{ bgcolor: 'primary.main', width: 34, height: 34, borderRadius: 2.5 }}>
          <WorkOutlineIcon fontSize="small" />
        </Avatar>
        <Typography variant="h6" fontWeight={800} sx={{ mr: 3, ml: 1 }}>Jobhunter</Typography>

        {staff && (
          <Box component="nav" sx={{ display: 'flex', flex: 1, overflowX: 'auto', alignItems: 'center' }}>
            {MAIN.map(([p, label]) => <NavButton key={p} active={page === p} onClick={() => go(p)}>{t(label)}</NavButton>)}
            <NavButton active={Boolean(inMore)} endIcon={<ExpandMoreIcon />} aria-haspopup="menu"
              onClick={(e: MouseEvent<HTMLButtonElement>) => setMoreAt(e.currentTarget)}>
              {inMore ? t(inMore[1]) : t('More')}
            </NavButton>
          </Box>
        )}
        {!staff && <Box sx={{ flex: 1 }} />}

        <Tooltip title={lang === 'vi' ? 'Switch to English' : 'Chuyển sang tiếng Việt'}>
          <Button size="small" onClick={() => setLang(lang === 'vi' ? 'en' : 'vi')} sx={{ minWidth: 0, fontWeight: 700 }}
            aria-label={lang === 'vi' ? 'Switch to English' : 'Chuyển sang tiếng Việt'}>
            {lang === 'vi' ? 'VI' : 'EN'}
          </Button>
        </Tooltip>
        <Tooltip title={dark ? t('Light mode') : t('Dark mode')}>
          <IconButton onClick={() => setMode(dark ? 'light' : 'dark')} aria-label={dark ? t('Light mode') : t('Dark mode')}>
            {dark ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
          </IconButton>
        </Tooltip>
        <Button onClick={(e) => setAccountAt(e.currentTarget)} aria-haspopup="menu" aria-label={t('Account menu')}
          sx={{ color: 'text.primary', gap: 1, pl: 0.5 }}>
          <Avatar sx={{ width: 32, height: 32, fontSize: 14, bgcolor: 'primary.main' }}>{initials(user.name || user.email)}</Avatar>
          <Box sx={{ display: { xs: 'none', sm: 'block' }, textAlign: 'left', lineHeight: 1.2 }}>
            <Typography variant="body2" fontWeight={600}>{user.name || user.email}</Typography>
            <Typography variant="caption" color="text.secondary">{t(ROLE_LABEL[user.role])}</Typography>
          </Box>
          <ExpandMoreIcon fontSize="small" />
        </Button>
      </Toolbar>

      <Menu anchorEl={moreAt} open={Boolean(moreAt)} onClose={() => setMoreAt(null)}>
        {MORE.map(([p, label]) => <MenuItem key={p} selected={page === p} onClick={() => go(p)}>{t(label)}</MenuItem>)}
        <Divider />
        <MenuItem component="a" href="/careers" target="_blank" onClick={() => setMoreAt(null)}>
          <ListItemText>{t('Careers site')}</ListItemText>
          <OpenInNewIcon fontSize="small" sx={{ ml: 2, color: 'text.secondary' }} />
        </MenuItem>
      </Menu>

      <Menu anchorEl={accountAt} open={Boolean(accountAt)} onClose={() => setAccountAt(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }} transformOrigin={{ vertical: 'top', horizontal: 'right' }}>
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="body2" fontWeight={600}>{user.name || user.email}</Typography>
          <Typography variant="caption" color="text.secondary" component="div">{user.email}</Typography>
        </Box>
        <Divider />
        {user.role === 'admin' && [
          <MenuItem key="users" selected={page === 'users'} onClick={() => go('users')}>
            <ListItemIcon><PeopleOutlineIcon fontSize="small" /></ListItemIcon>{t('Users')}
          </MenuItem>,
          <MenuItem key="templates" selected={page === 'templates'} onClick={() => go('templates')}>
            <ListItemIcon><MailOutlineIcon fontSize="small" /></ListItemIcon>{t('Email templates')}
          </MenuItem>,
          <Divider key="d" />,
        ]}
        {user.google_connected ? (
          <MenuItem onClick={disconnect}>
            <ListItemIcon><EventIcon fontSize="small" /></ListItemIcon>
            <ListItemText secondary={t('Click to disconnect')}>Google Calendar</ListItemText>
            <Chip size="small" color="success" label={t('Connected')} sx={{ ml: 2 }} />
          </MenuItem>
        ) : (
          <MenuItem onClick={connect}>
            <ListItemIcon><EventIcon fontSize="small" /></ListItemIcon>{t('Connect Google Calendar')}
          </MenuItem>
        )}
        <Divider />
        <MenuItem onClick={() => { setAccountAt(null); onSignOut() }}>
          <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>{t('Sign out')}
        </MenuItem>
      </Menu>
    </AppBar>
  )
}
