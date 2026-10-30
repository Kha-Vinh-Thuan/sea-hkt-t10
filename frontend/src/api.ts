// Typed calls to the FastAPI backend (proxied at /api by Vite). Recruiter calls carry the login token.

export type Stage = 'new' | 'screening' | 'interview' | 'offer' | 'hired' | 'rejected'

export const STAGE_LABEL: Record<Stage, string> = {
  new: 'New', screening: 'Screening', interview: 'Interview', offer: 'Offer', hired: 'Hired', rejected: 'Rejected',
}

export type EmploymentType = 'full_time' | 'part_time' | 'internship' | 'contract'

export const EMPLOYMENT_LABEL: Record<EmploymentType, string> = {
  full_time: 'Full-time', part_time: 'Part-time', internship: 'Internship', contract: 'Contract',
}

export type PublicJob = {
  id: number
  title: string
  department: string
  location: string
  description: string
  requirements: string
  employment_type: EmploymentType
  is_remote: boolean
  salary_min: number | null // monthly, VND
  salary_max: number | null
  expected_degree: string
  opens_on: string | null // YYYY-MM-DD
  closes_on: string | null
}

export type Job = PublicJob & {
  interview_duration_minutes: number
  openings: number
  is_open: boolean
  applicant_count: number
  hired_count: number
}

export type JobInput = Omit<Job, 'id' | 'applicant_count' | 'hired_count'>

export type Applicant = {
  id: number
  job_id: number
  name: string
  email: string
  phone: string
  stage: Stage
  cv_filename: string
  created_at: string
  linkedin: string
  short_intro: string
  notes: string
  priority: number
  tags: string[]
  available_from: string | null
  degree: string
  salary_expected: number | null
  salary_proposed: number | null
  archived: boolean
  refuse_reason: RefuseReason | null
  refused_at: string | null
  stage_changed_at: string
}

export type RefuseReason = 'does_not_fit' | 'refused_job_fit' | 'refused_salary' | 'job_filled' | 'duplicate' | 'spam'

export const REFUSE_REASON_LABEL: Record<RefuseReason, string> = {
  does_not_fit: 'Does not fit the job requirements',
  refused_job_fit: 'Refused by applicant: job fit',
  refused_salary: 'Refused by applicant: salary',
  job_filled: 'Job already filled',
  duplicate: 'Duplicate',
  spam: 'Spam',
}

// Fields the recruiter edits in the side panel (PATCH /applicants/{id}).
export type ApplicantUpdate = Pick<Applicant,
  'notes' | 'priority' | 'tags' | 'linkedin' | 'available_from' | 'degree' | 'salary_expected' | 'salary_proposed'>

export type Interview = {
  id: number
  applicant_id: number
  interviewer_name: string
  interviewer_email: string
  start: string
  end: string
  location: string
  status: InterviewStatus
  sequence: number
  score: number | null
  recommendation: Recommendation | null
  feedback: string
}

export type InterviewStatus = 'scheduled' | 'done' | 'no_show' | 'cancelled'
export type Recommendation = 'hire' | 'maybe' | 'no_hire'
export const INTERVIEW_STATUS_LABEL: Record<InterviewStatus, string> = {
  scheduled: 'Scheduled', done: 'Done', no_show: 'No-show', cancelled: 'Cancelled',
}
export const INTERVIEW_STATUS_COLOR: Record<InterviewStatus, 'primary' | 'success' | 'warning' | 'default'> = {
  scheduled: 'primary', done: 'success', no_show: 'warning', cancelled: 'default',
}
export const RECOMMENDATION_LABEL: Record<Recommendation, string> = { hire: 'Hire', maybe: 'Maybe', no_hire: 'No hire' }
export type FeedbackInput = {
  status: 'done' | 'no_show'; score: number | null; recommendation: Recommendation | null; feedback: string
}
export type InterviewResult = { interview: Interview; emailed: boolean; mail_error: string | null }

export type UpcomingInterview = Interview & { applicant_name: string; job_title: string }

export type ApplicantDetail = Applicant & {
  cv_text: string
  activity: { id: number; message: string; created_at: string }[]
  interviews: Interview[]
}

export type InterviewInput = { start: string; interviewer_name: string; interviewer_email: string; location: string }

// ponytail: token in localStorage is fine for a localhost demo; move to an httpOnly cookie before going public.
const TOKEN_KEY = 'hr_token'

export const session = {
  token: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  save: (token: string) => { try { localStorage.setItem(TOKEN_KEY, token) } catch { /* private mode */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ } },
}

export class UnauthorizedError extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = session.token()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`/api${path}`, { ...init, headers })
  if (response.status === 401 && !path.startsWith('/auth')) {
    session.clear()
    throw new UnauthorizedError('Please sign in')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    // FastAPI validation errors come back as a list of {msg}.
    const detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join(', ') : body.detail
    throw new Error(detail ?? `HTTP ${response.status}`)
  }
  return response.json()
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  publicJobs: () => request<PublicJob[]>('/public/jobs'),
  publicJob: (id: number) => request<PublicJob>(`/public/jobs/${id}`),
  apply: (id: number, form: FormData) => request<{ id: number }>(`/public/jobs/${id}/apply`, { method: 'POST', body: form }),

  login: (email: string, password: string) =>
    request<{ token: string; email: string }>('/auth/login', json('POST', { email, password })),

  jobs: () => request<Job[]>('/jobs'),
  createJob: (job: JobInput) => request<Job>('/jobs', json('POST', job)),
  updateJob: (id: number, job: JobInput) => request<Job>(`/jobs/${id}`, json('PUT', job)),
  stages: () => request<Stage[]>('/stages'),
  applicants: (jobId: number) => request<Applicant[]>(`/applicants?job_id=${jobId}`),
  applicant: (id: number) => request<ApplicantDetail>(`/applicants/${id}`),
  moveStage: (id: number, stage: Stage) => request<Applicant>(`/applicants/${id}/stage`, json('PATCH', { stage })),
  updateApplicant: (id: number, data: Partial<ApplicantUpdate>) =>
    request<Applicant>(`/applicants/${id}`, json('PATCH', data)),
  refuse: (id: number, reason: RefuseReason, sendEmail: boolean) =>
    request<{ applicant: Applicant; emailed: boolean; mail_error: string | null }>(
      `/applicants/${id}/refuse`, json('POST', { reason, send_email: sendEmail })),
  archive: (id: number) => request<Applicant>(`/applicants/${id}/archive`, { method: 'POST' }),
  restore: (id: number) => request<Applicant>(`/applicants/${id}/restore`, { method: 'POST' }),
  scheduleInterview: (id: number, data: InterviewInput) =>
    request<{ interview: Interview; emailed: boolean; mail_error: string | null }>(
      `/applicants/${id}/interviews`, json('POST', data)),
  interviews: () => request<UpcomingInterview[]>('/interviews'),
  rescheduleInterview: (id: number, data: InterviewInput) =>
    request<InterviewResult>(`/interviews/${id}`, json('PUT', data)),
  cancelInterview: (id: number) => request<InterviewResult>(`/interviews/${id}/cancel`, { method: 'POST' }),
  interviewFeedback: (id: number, data: FeedbackInput) =>
    request<Interview>(`/interviews/${id}/feedback`, json('POST', data)),

  // The CV link needs the token too, so download through fetch instead of a plain <a href>.
  downloadCv: async (id: number, filename: string) => {
    const response = await fetch(`/api/applicants/${id}/cv`, { headers: { Authorization: `Bearer ${session.token()}` } })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const url = URL.createObjectURL(await response.blob())
    const link = Object.assign(document.createElement('a'), { href: url, download: filename })
    link.click()
    URL.revokeObjectURL(url)
  },
}

export function formatWhen(iso: string) {
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
