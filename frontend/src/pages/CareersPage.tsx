// Public careers site: list of open jobs, or one job with its apply form.
import { useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Container, Link, Stack,
  Typography,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined'
import { api, type PublicJob } from '../api'
import ApplyForm from '../components/ApplyForm'

function JobMeta({ job }: { job: PublicJob }) {
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
      {job.department && <Chip size="small" label={job.department} />}
      {job.location && <Chip size="small" variant="outlined" icon={<PlaceOutlinedIcon />} label={job.location} />}
    </Stack>
  )
}

function JobList() {
  const [jobs, setJobs] = useState<PublicJob[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { api.publicJobs().then(setJobs).catch((e: Error) => setError(e.message)) }, [])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!jobs) return <CircularProgress />
  if (!jobs.length) return <Typography color="text.secondary">No open positions right now.</Typography>
  return (
    <Stack spacing={2}>
      {jobs.map((job) => (
        <Card key={job.id} variant="outlined">
          <CardActionArea href={`/careers/${job.id}`}>
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
        <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>About the role</Typography>
        <Typography sx={{ whiteSpace: 'pre-line' }}>{job.description}</Typography>
        {job.requirements && (
          <>
            <Typography variant="h6" sx={{ mt: 4, mb: 1 }}>Requirements</Typography>
            <Typography sx={{ whiteSpace: 'pre-line' }}>{job.requirements}</Typography>
          </>
        )}
      </Box>
      <Card variant="outlined" sx={{ position: { md: 'sticky' }, top: 24 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} gutterBottom>Apply for this job</Typography>
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
          <Typography variant="h3" fontWeight={800}>Join our team</Typography>
          <Typography sx={{ mt: 1, opacity: 0.85 }}>Find a role where you can do your best work.</Typography>
        </Container>
      </Box>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {jobId !== undefined && (
          <Button component={Link} href="/careers" startIcon={<ArrowBackIcon />} sx={{ mb: 3 }}>All jobs</Button>
        )}
        {jobId === undefined ? <JobList /> : <JobDetail jobId={jobId} />}
      </Container>
    </Box>
  )
}
