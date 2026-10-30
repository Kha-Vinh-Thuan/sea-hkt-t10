// Public careers site: list of open jobs, or one job with its apply form.
import { useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Container, Link, MenuItem, Stack,
  TextField, Typography,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined'
import { api, EMPLOYMENT_LABEL, type PublicJob } from '../api'
import ApplyForm from '../components/ApplyForm'
import LangSwitch from '../components/LangSwitch'
import { locale, t } from '../i18n'

const vnd = (n: number) => n.toLocaleString(locale())

function salaryLabel({ salary_min: min, salary_max: max }: PublicJob) {
  if (min !== null && max !== null) return min === max ? `${vnd(min)} VND` : `${vnd(min)} – ${vnd(max)} VND`
  if (min !== null) return t('From {amount} VND', { amount: vnd(min) })
  if (max !== null) return t('Up to {amount} VND', { amount: vnd(max) })
  return ''
}

function JobMeta({ job }: { job: PublicJob }) {
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
      {job.location && <Chip size="small" variant="outlined" icon={<PlaceOutlinedIcon />} label={job.location} />}
      <Chip size="small" variant="outlined" label={t(EMPLOYMENT_LABEL[job.employment_type])} />
      {job.is_remote && <Chip size="small" color="primary" variant="outlined" label={t('Remote')} />}
    </Stack>
  )
}

// ponytail: plain text + clickable bare http(s) URLs; swap for a markdown renderer if rich formatting is needed.
function Linkified({ text }: { text: string }) {
  // split() with a capture group keeps the URLs at odd indexes; trailing punctuation stays outside the link.
  return text.split(/(https?:\/\/[^\s<>"]*[^\s<>".,;:!?)])/).map((part, i) => (i % 2
    ? <Link key={i} href={part} target="_blank" rel="noopener noreferrer">{part}</Link>
    : part))
}

// Every filter value maps to a predicate; '' means "any".
type Filters = { location: string; employment_type: string; remote: string }
const NO_FILTERS: Filters = { location: '', employment_type: '', remote: '' }

function matches(job: PublicJob, f: Filters) {
  return (!f.location || job.location === f.location)
    && (!f.employment_type || job.employment_type === f.employment_type)
    && (!f.remote || String(job.is_remote) === f.remote)
}

function FilterSelect({ label, value, options, onChange }: {
  label: string; value: string; options: [string, string][]; onChange: (value: string) => void
}) {
  return (
    <TextField select size="small" label={label} value={value} onChange={(e) => onChange(e.target.value)}
      sx={{ minWidth: 170 }}>
      <MenuItem value="">{t('Any')}</MenuItem>
      {options.map(([v, text]) => <MenuItem key={v} value={v}>{t(text)}</MenuItem>)}
    </TextField>
  )
}

function JobList() {
  const [jobs, setJobs] = useState<PublicJob[] | null>(null)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)

  useEffect(() => { api.publicJobs().then(setJobs).catch((e: Error) => setError(e.message)) }, [])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!jobs) return <CircularProgress />
  if (!jobs.length) return <Typography color="text.secondary">{t('No open positions right now.')}</Typography>

  const distinct = (key: 'location') =>
    [...new Set(jobs.map((j) => j[key]).filter(Boolean))].sort().map((v): [string, string] => [v, v])
  const set = (key: keyof Filters) => (value: string) => setFilters({ ...filters, [key]: value })
  const shown = jobs.filter((job) => matches(job, filters))
  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1.5, alignItems: 'center' }}>
        <FilterSelect label={t('Location')} value={filters.location} options={distinct('location')} onChange={set('location')} />
        <FilterSelect label={t('Employment type')} value={filters.employment_type}
          options={Object.entries(EMPLOYMENT_LABEL)} onChange={set('employment_type')} />
        <FilterSelect label={t('Remote')} value={filters.remote} options={[['true', 'Remote'], ['false', 'On-site']]}
          onChange={set('remote')} />
        {shown.length < jobs.length && <Button onClick={() => setFilters(NO_FILTERS)}>{t('Clear filters')}</Button>}
      </Stack>
      {!shown.length && <Typography color="text.secondary">{t('No jobs match these filters.')}</Typography>}
      {shown.map((job) => (
        <Card key={job.id} variant="outlined">
          <CardActionArea href={`/careers/${job.id}${window.location.search}`}>
            <CardContent>
              <Typography variant="h6" fontWeight={700} gutterBottom>{job.title}</Typography>
              <JobMeta job={job} />
              <Typography color="text.secondary" sx={{ mt: 1.5 }}>{job.description}</Typography>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
    </Stack>
  )
}

function JobDetail({ jobId }: { jobId: number }) {
  const [job, setJob] = useState<PublicJob | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { api.publicJob(jobId).then(setJob).catch((e: Error) => setError(e.message)) }, [jobId])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!job) return <CircularProgress />
  return (
    <Box sx={{ display: 'grid', gap: 4, gridTemplateColumns: { md: '3fr 2fr' }, alignItems: 'start' }}>
      <Box>
        <Typography variant="h4" fontWeight={800} gutterBottom>{job.title}</Typography>
        <JobMeta job={job} />
        <Stack spacing={0.5} sx={{ mt: 2 }}>
          {salaryLabel(job) && <Typography><b>{t('Salary:')}</b> {t('{salary} / month', { salary: salaryLabel(job) })}</Typography>}
          {job.expected_degree && <Typography><b>{t('Degree:')}</b> {job.expected_degree}</Typography>}
          {job.closes_on && (
            <Typography><b>{t('Apply by:')}</b> {new Date(`${job.closes_on}T00:00`).toLocaleDateString(locale())}</Typography>
          )}
        </Stack>
        <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>{t('About the role')}</Typography>
        <Typography sx={{ whiteSpace: 'pre-line' }}><Linkified text={job.description} /></Typography>
        {job.requirements && (
          <>
            <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>{t('Requirements')}</Typography>
            <Typography sx={{ whiteSpace: 'pre-line' }}><Linkified text={job.requirements} /></Typography>
          </>
        )}
      </Box>
      <Card variant="outlined" sx={{ position: { md: 'sticky' }, top: 24 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} gutterBottom>{t('Apply for this job')}</Typography>
          <ApplyForm jobId={job.id} />
        </CardContent>
      </Card>
    </Box>
  )
}

export default function CareersPage({ jobId }: { jobId?: number }) {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Box sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', py: { xs: 5, md: 7 } }}>
        <Container maxWidth="lg">
          <Stack direction="row" sx={{ alignItems: 'flex-start' }}>
            <Typography variant="h3" fontWeight={800} sx={{ flex: 1 }}>{t('Join our team')}</Typography>
            <LangSwitch color="inherit" />
          </Stack>
          <Typography sx={{ mt: 1, opacity: 0.85 }}>{t('Find a role where you can do your best work.')}</Typography>
        </Container>
      </Box>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {jobId !== undefined && (
          <Button component={Link} href="/careers" startIcon={<ArrowBackIcon />} sx={{ mb: 3 }}>{t('All jobs')}</Button>
        )}
        {jobId === undefined ? <JobList /> : <JobDetail jobId={jobId} />}
      </Container>
    </Box>
  )
}
