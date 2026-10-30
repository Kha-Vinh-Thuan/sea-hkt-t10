// Talent pools (Odoo hr.talent.pool): named groups of applicants to contact again later.
// Left: pools (create / delete). Right: members of the selected pool (name, email, job; remove).
// Applicants are added from the applicant drawer.
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, CardContent, Chip, IconButton, List, ListItemButton, ListItemText, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Typography,
} from '@mui/material'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { api, STAGE_LABEL, type PoolMember, type TalentPool } from '../api'

export default function TalentPoolsPage({ onError }: { onError: (e: Error) => void }) {
  const [pools, setPools] = useState<TalentPool[]>([])
  const [poolId, setPoolId] = useState<number>()
  const [members, setMembers] = useState<PoolMember[]>([])
  const [draft, setDraft] = useState({ name: '', description: '' })
  const [error, setError] = useState('')

  const fail = useCallback((e: Error) => { setError(e.message); onError(e) }, [onError])
  const loadPools = useCallback(() => api.talentPools().then(setPools).catch(fail), [fail])
  useEffect(() => { loadPools() }, [loadPools])
  useEffect(() => {
    setMembers([])
    if (poolId !== undefined) api.poolMembers(poolId).then(setMembers).catch(fail)
  }, [poolId, fail])

  async function create() {
    try {
      const pool = await api.createTalentPool(draft)
      setDraft({ name: '', description: '' })
      await loadPools()
      setPoolId(pool.id)
    } catch (e) { fail(e as Error) }
  }

  async function remove(pool: TalentPool) {
    if (!window.confirm(`Delete the pool "${pool.name}"? Its applicants are kept.`)) return
    try {
      await api.deleteTalentPool(pool.id)
      if (poolId === pool.id) setPoolId(undefined)
      await loadPools()
    } catch (e) { fail(e as Error) }
  }

  async function removeMember(applicantId: number) {
    if (poolId === undefined) return
    try {
      await api.removePoolMember(poolId, applicantId)
      setMembers(await api.poolMembers(poolId))
      await loadPools()
    } catch (e) { fail(e as Error) }
  }

  const selected = pools.find((p) => p.id === poolId)

  return (
    <Stack spacing={2}>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: 'flex-start' }}>
        <Card variant="outlined" sx={{ width: { xs: '100%', md: 320 }, flexShrink: 0 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={700}>Talent pools</Typography>
            <List dense>
              {pools.map((p) => (
                <ListItemButton key={p.id} selected={p.id === poolId} onClick={() => setPoolId(p.id)}>
                  <ListItemText primary={p.name} secondary={p.description || undefined} />
                  <Chip size="small" label={p.member_count} sx={{ mr: 1 }} />
                  <IconButton size="small" aria-label={`Delete ${p.name}`}
                    onClick={(e) => { e.stopPropagation(); remove(p) }}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </ListItemButton>
              ))}
              {!pools.length && <ListItemText sx={{ px: 2 }} secondary="No pools yet." />}
            </List>
            <Stack spacing={1}>
              <TextField size="small" label="New pool name" value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              <TextField size="small" label="Description" value={draft.description}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
              <Button variant="contained" disabled={!draft.name.trim()} onClick={create}>Create pool</Button>
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined" sx={{ flex: 1, width: '100%' }}>
          <CardContent sx={{ overflowX: 'auto' }}>
            {!selected ? (
              <Typography color="text.secondary">Select a pool to see its applicants.</Typography>
            ) : (
              <>
                <Typography variant="subtitle1" fontWeight={700} gutterBottom>{selected.name}</Typography>
                {!members.length ? (
                  <Typography color="text.secondary">No applicants yet. Add them from the applicant panel.</Typography>
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Email</TableCell>
                        <TableCell>Job</TableCell>
                        <TableCell>Stage</TableCell>
                        <TableCell />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {members.map((m) => (
                        <TableRow key={m.id}>
                          <TableCell>{m.name}</TableCell>
                          <TableCell>{m.email}</TableCell>
                          <TableCell>{m.job_title}</TableCell>
                          <TableCell>{STAGE_LABEL[m.stage]}</TableCell>
                          <TableCell align="right">
                            <Button size="small" onClick={() => removeMember(m.id)}>Remove</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Stack>
  )
}
