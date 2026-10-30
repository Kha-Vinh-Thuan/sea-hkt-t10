// Talent pools in the applicant drawer: chips for the pools the applicant is in (delete = remove), and an
// "Add to pool" select listing the others.
import { useCallback, useEffect, useState } from 'react'
import { Box, Chip, MenuItem, Stack, TextField } from '@mui/material'
import { api, type TalentPool } from '../api'

type Props = { applicantId: number; onError: (message: string) => void; onChanged: () => void }

export default function TalentPoolPicker({ applicantId, onError, onChanged }: Props) {
  const [pools, setPools] = useState<TalentPool[]>([])
  const [memberOf, setMemberOf] = useState<number[]>([])

  const load = useCallback(() => Promise.all([api.talentPools(), api.applicantPools(applicantId)])
    .then(([p, m]) => { setPools(p); setMemberOf(m) })
    .catch((e: Error) => onError(e.message)), [applicantId, onError])
  useEffect(() => { load() }, [load])

  async function change(action: () => Promise<unknown>) {
    try {
      await action()
      await load()
      onChanged() // the activity log gained a line
    } catch (e) { onError((e as Error).message) }
  }

  const others = pools.filter((p) => !memberOf.includes(p.id))
  if (!pools.length) return null
  return (
    <Box>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mb: memberOf.length ? 1 : 0 }}>
        {pools.filter((p) => memberOf.includes(p.id)).map((p) => (
          <Chip key={p.id} size="small" color="secondary" label={`Pool: ${p.name}`}
            onDelete={() => change(() => api.removePoolMember(p.id, applicantId))} />
        ))}
      </Stack>
      {others.length > 0 && (
        <TextField select size="small" fullWidth label="Add to pool" value=""
          onChange={(e) => change(() => api.addPoolMember(Number(e.target.value), applicantId))}>
          {others.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
        </TextField>
      )}
    </Box>
  )
}
