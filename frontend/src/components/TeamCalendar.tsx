// Week grid (Mon–Fri, working hours) with the busy blocks of several interviewers on top of each other, one colour
// each, like Odoo's attendee calendar. Only busy times are shown, never what the meeting is. Clicking a free cell
// picks that start time for the given interviewer (the first ticked one that is free there).
import { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Checkbox, Chip, FormControlLabel, IconButton, Stack, Tooltip, Typography } from '@mui/material'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import { api, type InterviewerBusy, type UserBrief } from '../api'

// Same as the backend's ASSUMPTION working hours (interviews/availability.py); rows every 30 minutes.
const DAY_START = 9
const DAY_END = 17
const STEP_MINUTES = 30
const ROW_PX = 22
const COLORS = ['#1976d2', '#ed6c02', '#2e7d32', '#9c27b0', '#d32f2f', '#0288d1']

type Props = {
  interviewers: UserBrief[]
  minutes: number // interview length: a cell is free only if the whole interview fits
  selected?: { start: string; userId: number }
  onPick: (start: Date, user: UserBrief) => void
}

function mondayOf(date: Date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return d
}

const overlaps = (aStart: number, aEnd: number, bStart: number, bEnd: number) => aStart < bEnd && aEnd > bStart

export default function TeamCalendar({ interviewers, minutes, selected, onPick }: Props) {
  const [weekStart, setWeekStart] = useState(() => mondayOf(new Date()))
  const [ticked, setTicked] = useState<number[]>(() => interviewers.map((u) => u.id))
  const [rows, setRows] = useState<InterviewerBusy[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { setTicked(interviewers.map((u) => u.id)) }, [interviewers])

  useEffect(() => {
    setRows(null)
    setError('')
    if (!ticked.length) return setRows([])
    api.teamBusy(ticked, weekStart, 5).then(setRows).catch((e: Error) => setError(e.message))
  }, [ticked, weekStart])

  const days = useMemo(() => [0, 1, 2, 3, 4].map((i) => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + i)
    return d
  }), [weekStart])
  const times = useMemo(() => {
    const out: number[] = []
    for (let m = DAY_START * 60; m < DAY_END * 60; m += STEP_MINUTES) out.push(m)
    return out
  }, [])
  const colorOf = (userId: number) => COLORS[interviewers.findIndex((u) => u.id === userId) % COLORS.length]
  const parsed = useMemo(() => (rows ?? []).map((r) => ({
    ...r, blocks: r.busy.map((b) => ({ ...b, s: Date.parse(b.start), e: Date.parse(b.end) })),
  })), [rows])

  function cellStart(day: Date, minute: number) {
    const d = new Date(day)
    d.setHours(0, minute, 0, 0)
    return d
  }

  // Ticked interviewers who are free for the whole interview starting at this cell.
  function freeAt(start: Date) {
    const s = start.getTime()
    const e = s + minutes * 60_000
    return parsed.filter((r) => !r.blocks.some((b) => overlaps(s, e, b.s, b.e)))
  }

  function shift(weeks: number) {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + weeks * 7)
    setWeekStart(d)
  }

  const now = Date.now()
  const googleProblems = parsed.filter((r) => r.google_connected && !r.google_ok)

  return (
    <Box>
      <Stack direction="row" sx={{ flexWrap: 'wrap', columnGap: 1, alignItems: 'center' }}>
        {interviewers.map((u) => (
          <FormControlLabel key={u.id} label={<Typography variant="body2">{u.name || u.email}</Typography>}
            control={<Checkbox size="small" checked={ticked.includes(u.id)} sx={{ color: colorOf(u.id), '&.Mui-checked': { color: colorOf(u.id) } }}
              onChange={(e) => setTicked((t) => (e.target.checked ? [...t, u.id] : t.filter((id) => id !== u.id)))} />} />
        ))}
      </Stack>
      <Stack direction="row" sx={{ alignItems: 'center', gap: 1, mb: 0.5 }}>
        <IconButton size="small" aria-label="Previous week" onClick={() => shift(-1)}><ChevronLeftIcon /></IconButton>
        <Typography variant="body2" fontWeight={600}>
          {days[0].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })} – {days[4].toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
        </Typography>
        <IconButton size="small" aria-label="Next week" onClick={() => shift(1)}><ChevronRightIcon /></IconButton>
        {parsed.filter((r) => !r.google_connected).map((r) => (
          <Chip key={r.user_id} size="small" variant="outlined" label={`${r.name}: no Google Calendar`} />
        ))}
      </Stack>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {googleProblems.length > 0 && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          Google Calendar could not be read for {googleProblems.map((r) => r.name).join(', ')}; only interviews booked here are shown.
        </Alert>
      )}

      <Box sx={{ overflowX: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: `48px repeat(5, minmax(72px, 1fr))`, minWidth: 420 }}>
          <Box />
          {days.map((d) => (
            <Typography key={d.toISOString()} variant="caption" fontWeight={600} sx={{ textAlign: 'center', py: 0.5, borderLeft: 1, borderColor: 'divider' }}>
              {d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}
            </Typography>
          ))}
          {times.map((minute) => (
            <Box key={minute} sx={{ display: 'contents' }}>
              <Typography variant="caption" color="text.secondary" sx={{ pr: 0.5, textAlign: 'right', lineHeight: `${ROW_PX}px` }}>
                {minute % 60 === 0 ? `${minute / 60}:00` : ''}
              </Typography>
              {days.map((day) => {
                const start = cellStart(day, minute)
                const s = start.getTime()
                const cellEnd = s + STEP_MINUTES * 60_000
                const busyHere = parsed.filter((r) => r.blocks.some((b) => overlaps(s, cellEnd, b.s, b.e)))
                const free = s > now ? freeAt(start) : []
                const isSelected = selected && Date.parse(selected.start) === s
                const label = busyHere.length
                  ? `Busy: ${busyHere.map((r) => r.name).join(', ')}`
                  : free.length ? `Free: ${free.map((r) => r.name).join(', ')} — click to pick` : ''
                return (
                  <Tooltip key={s} title={label} disableInteractive>
                    <Box
                      role={free.length ? 'button' : undefined}
                      aria-label={free.length ? `${start.toLocaleString()} ${label}` : undefined}
                      tabIndex={free.length ? 0 : -1}
                      onClick={() => {
                        const user = interviewers.find((u) => u.id === free[0]?.user_id)
                        if (user) onPick(start, user)
                      }}
                      onKeyDown={(e) => {
                        const user = interviewers.find((u) => u.id === free[0]?.user_id)
                        if (user && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onPick(start, user) }
                      }}
                      sx={{
                        height: ROW_PX, borderLeft: 1, borderTop: minute % 60 === 0 ? 1 : 0, borderColor: 'divider',
                        display: 'flex', gap: '2px', px: '2px', alignItems: 'stretch',
                        bgcolor: isSelected ? 'primary.light' : s <= now ? 'action.disabledBackground' : undefined,
                        cursor: free.length ? 'pointer' : 'default',
                        '&:hover': free.length ? { bgcolor: 'action.hover' } : undefined,
                      }}>
                      {busyHere.map((r) => (
                        <Box key={r.user_id} sx={{ flex: 1, bgcolor: colorOf(r.user_id), opacity: 0.75, borderRadius: '2px' }} />
                      ))}
                    </Box>
                  </Tooltip>
                )
              })}
            </Box>
          ))}
        </Box>
      </Box>
      {rows === null && !error && <Typography variant="caption">Loading calendars…</Typography>}
      <Typography variant="caption" color="text.secondary" component="div">
        Coloured = busy (interview here or Google Calendar). Click a free cell to pick it; the time is re-checked when you book.
      </Typography>
    </Box>
  )
}
