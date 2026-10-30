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
  tags: string[]
  opens_on: string | null // YYYY-MM-DD
  closes_on: string | null
}

export type Job = PublicJob & {
  interview_duration_minutes: number
  openings: number
  is_open: boolean
  applicant_count: number
  hired_count: number
  interviewer_ids: number[]
  recruiter_id: number | null
  manager_id: number | null
}

export type JobInput = Omit<Job, 'id' | 'applicant_count' | 'hired_count'>

// Where the applicant came from (Odoo UTM source, simplified). Careers links can carry it: /careers/1?source=linkedin
export type Source = 'careers_site' | 'linkedin' | 'referral' | 'job_board' | 'other'

export const SOURCE_LABEL: Record<Source, string> = {
  careers_site: 'Careers site', linkedin: 'LinkedIn', referral: 'Referral', job_board: 'Job board', other: 'Other',
}

export type Role = 'admin' | 'recruiter' | 'interviewer'
export const ROLE_LABEL: Record<Role, string> = { admin: 'Admin', recruiter: 'Recruiter', interviewer: 'Interviewer' }
export type UserBrief = { id: number; name: string; email: string; role: Role }
export type Me = UserBrief & { google_connected: boolean }
export type User = UserBrief & { is_active: boolean; created_at: string }
export type UserInput = { email: string; name: string; role: Role; password: string }
export type UserUpdate = Partial<Pick<User, 'name' | 'role' | 'is_active'>>

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
  source: Source
  source_detail: string
  next_action: string
  next_action_due: string | null // YYYY-MM-DD
  hired_at: string | null // set when moved into `hired`, cleared when moved out
  next_action_user_id: number | null // who does the next step
  user_id: number | null // recruiter owner
}

// GET /stage-rules: requirements = what must be true to leave the stage ('' = none).
export type StageRules = { stuck_after_days: Record<Stage, number | null>; requirements: Record<Stage, string> }

// GET /reports/summary: one row per job; the count maps hold every key, zero included.
export type JobReport = {
  job_id: number
  title: string
  is_open: boolean
  total: number
  by_stage: Record<Stage, number>
  hired: number
  openings: number
  avg_days_to_hire: number | null
  by_source: Record<Source, number>
  refused_by_reason: Record<RefuseReason, number>
}

export type TalentPool = { id: number; name: string; description: string; created_at: string; member_count: number }
export type TalentPoolInput = { name: string; description: string }
export type PoolMember = { id: number; name: string; email: string; job_id: number; job_title: string; stage: Stage }

// Days in a stage before a card counts as stuck; null = never. Filled from GET /stage-rules by loadStageRules().
let stuckAfterDays: Partial<Record<Stage, number | null>> = {}
export const loadStageRules = () =>
  request<StageRules>('/stage-rules').then((r) => { stuckAfterDays = r.stuck_after_days })

// Whole days since the applicant entered the current stage.
export const daysInStage = (a: Pick<Applicant, 'stage_changed_at'>) =>
  Math.floor((Date.now() - Date.parse(a.stage_changed_at)) / 86_400_000)

export function isStuck(a: Pick<Applicant, 'stage' | 'stage_changed_at'>) {
  const limit = stuckAfterDays[a.stage]
  return limit != null && daysInStage(a) >= limit
}

export type RefuseReason = 'does_not_fit' | 'refused_job_fit' | 'refused_salary' | 'job_filled' | 'duplicate' | 'spam'

// GET /refuse-reasons: the backend owns both the list and its labels.
export type RefuseReasonOption = { value: RefuseReason; label: string }

// Optional board filters for GET /applicants; empty values are left out of the query string.
export type ApplicantFilters = { q?: string; priority_min?: number; tag?: string; archived?: boolean; owner?: 'me' }

// Fields the recruiter edits in the side panel (PATCH /applicants/{id}).
export type ApplicantUpdate = Pick<Applicant,
  'notes' | 'priority' | 'tags' | 'linkedin' | 'available_from' | 'degree' | 'salary_expected' | 'salary_proposed'
  | 'source' | 'source_detail' | 'next_action' | 'next_action_due' | 'next_action_user_id' | 'user_id'>

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
  google_event_id: string // '' = not on the interviewer's Google Calendar
  meet_url: string
  candidate_response: CandidateResponse
}

export type CandidateResponse = 'none' | 'accepted' | 'declined'
export const CANDIDATE_RESPONSE_LABEL: Record<CandidateResponse, string> = {
  none: 'No answer yet', accepted: 'Candidate accepted', declined: 'Candidate declined',
}
export type Slot = { start: string; end: string }

// GET /interviewers/busy: busy blocks only (our interviews + Google free/busy), never Google event titles.
export type BusyBlock = Slot & { source: 'interview' | 'google' }
export type InterviewerBusy = {
  user_id: number; name: string; email: string; google_connected: boolean; google_ok: boolean; busy: BusyBlock[]
}

// Public pages (no login): the candidate's booking link and Accept / Decline link.
export type BookingPage = {
  job_title: string; candidate_name: string; minutes: number; location: string; expires_at: string; slots: Slot[]
}
export type CandidateInterview = {
  job_title: string; candidate_name: string; start: string; end: string; location: string; meet_url: string
  status: InterviewStatus; candidate_response: CandidateResponse
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
  other_applications: OtherApplication[]
  attachments: Attachment[]
}

// Files other than the CV (PDF / DOCX / TXT / PNG / JPG, max 5 MB).
export type Attachment = { id: number; applicant_id: number; filename: string; content_type: string; size: number; created_at: string }

// Same person (email any case, or phone) applying to another job: Odoo's "application_count".
export type OtherApplication = {
  id: number; job_id: number; job_title: string; stage: Stage; archived: boolean; created_at: string
}

// Editable email texts with {name} / {job} / {company}; `key` marks the seeded ones the app sends by itself.
export type MailTemplate = { id: number; key: string | null; name: string; subject: string; body: string; stage: Stage | null }
export type MailTemplateInput = Pick<MailTemplate, 'name' | 'subject' | 'body' | 'stage'>
export type EmailDraft = { subject: string; body: string }

export type InterviewInput = { start: string; interviewer_name: string; interviewer_email: string; location: string }

// ponytail: token in localStorage is fine for a localhost demo; move to an httpOnly cookie before going public.
const TOKEN_KEY = 'hr_token'
const USER_KEY = 'hr_user'

// The stored user only picks the screen; the server re-checks the role on every call.
export const session = {
  token: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  user: (): UserBrief | null => { try { return JSON.parse(localStorage.getItem(USER_KEY) ?? 'null') } catch { return null } },
  save: (token: string, user: UserBrief) => {
    try { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(USER_KEY, JSON.stringify(user)) } catch { /* private mode */ }
  },
  saveUser: (user: UserBrief) => { try { localStorage.setItem(USER_KEY, JSON.stringify(user)) } catch { /* private mode */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY) } catch { /* private mode */ } },
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
  // 204 No Content (deletes, pool membership) has no body to parse.
  return response.status === 204 ? (null as T) : response.json()
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
    request<{ token: string; email: string; user: UserBrief }>('/auth/login', json('POST', { email, password })),
  me: () => request<Me>('/auth/me'),
  googleConnectUrl: () => request<{ url: string }>('/google/connect'),
  googleDisconnect: () => request<null>('/google/connection', { method: 'DELETE' }),
  users: (role?: Role) => request<UserBrief[]>(`/users${role ? `?role=${role}` : ''}`),
  adminUsers: () => request<User[]>('/admin/users'),
  createUser: (data: UserInput) => request<User>('/admin/users', json('POST', data)),
  updateUser: (id: number, data: UserUpdate) => request<User>(`/admin/users/${id}`, json('PATCH', data)),
  resetPassword: (id: number, password: string) => request<User>(`/admin/users/${id}/password`, json('POST', { password })),

  jobs: () => request<Job[]>('/jobs'),
  createJob: (job: JobInput) => request<Job>('/jobs', json('POST', job)),
  updateJob: (id: number, job: JobInput) => request<Job>(`/jobs/${id}`, json('PUT', job)),
  stages: () => request<Stage[]>('/stages'),
  stageRules: () => request<StageRules>('/stage-rules'),
  reportSummary: () => request<JobReport[]>('/reports/summary'),
  talentPools: () => request<TalentPool[]>('/talent-pools'),
  createTalentPool: (data: TalentPoolInput) => request<TalentPool>('/talent-pools', json('POST', data)),
  deleteTalentPool: (id: number) => request<null>(`/talent-pools/${id}`, { method: 'DELETE' }),
  poolMembers: (id: number) => request<PoolMember[]>(`/talent-pools/${id}/members`),
  addPoolMember: (id: number, applicantId: number) =>
    request<null>(`/talent-pools/${id}/members`, json('POST', { applicant_id: applicantId })),
  removePoolMember: (id: number, applicantId: number) =>
    request<null>(`/talent-pools/${id}/members/${applicantId}`, { method: 'DELETE' }),
  applicantPools: (applicantId: number) => request<number[]>(`/applicants/${applicantId}/talent-pools`),
  applicants: (jobId: number, filters: ApplicantFilters = {}) => {
    const params = new URLSearchParams({ job_id: String(jobId) })
    for (const [key, value] of Object.entries(filters)) if (value !== undefined && value !== '') params.set(key, String(value))
    return request<Applicant[]>(`/applicants?${params}`)
  },
  refuseReasons: () => request<RefuseReasonOption[]>('/refuse-reasons'),
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
  freeSlots: (userId: number, applicantId: number, days = 7) =>
    request<Slot[]>(`/interviewers/${userId}/free-slots?applicant_id=${applicantId}&days=${days}`),
  teamBusy: (userIds: number[], start: Date, days = 5) => {
    const params = new URLSearchParams({ start: start.toISOString(), days: String(days) })
    for (const id of userIds) params.append('user_ids', String(id))
    return request<InterviewerBusy[]>(`/interviewers/busy?${params}`)
  },
  proposeSlots: (applicantId: number, data: { interviewer_id: number; slots: string[]; location: string }) =>
    request<{ id: number; link: string; emailed: boolean; mail_error: string | null }>(
      `/applicants/${applicantId}/slot-proposals`, json('POST', data)),
  bookingPage: (token: string) => request<BookingPage>(`/public/bookings/${encodeURIComponent(token)}`),
  bookSlot: (token: string, start: string) =>
    request<{ start: string; end: string; location: string; meet_url: string }>(
      `/public/bookings/${encodeURIComponent(token)}`, json('POST', { start })),
  candidateInterview: (token: string) =>
    request<CandidateInterview>(`/public/interviews/${encodeURIComponent(token)}`),
  answerInterview: (token: string, answer: 'accepted' | 'declined') =>
    request<CandidateInterview>(`/public/interviews/${encodeURIComponent(token)}/response?answer=${answer}`,
      { method: 'POST' }),

  mailTemplates: () => request<MailTemplate[]>('/mail-templates'),
  createMailTemplate: (data: MailTemplateInput) => request<MailTemplate>('/admin/mail-templates', json('POST', data)),
  updateMailTemplate: (id: number, data: MailTemplateInput) =>
    request<MailTemplate>(`/admin/mail-templates/${id}`, json('PUT', data)),
  deleteMailTemplate: (id: number) => request<null>(`/admin/mail-templates/${id}`, { method: 'DELETE' }),
  composeEmail: (id: number, templateId: number) =>
    request<EmailDraft>(`/applicants/${id}/compose?template_id=${templateId}`),
  sendEmail: (id: number, draft: EmailDraft) =>
    request<{ sent: boolean; error: string | null }>(`/applicants/${id}/emails`, json('POST', draft)),

  copyApplicant: (id: number, jobId: number) => request<Applicant>(`/applicants/${id}/copy`, json('POST', { job_id: jobId })),
  uploadAttachment: (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Attachment>(`/applicants/${id}/attachments`, { method: 'POST', body: form })
  },
  deleteAttachment: async (id: number, attachmentId: number) => {
    // 204 has no body, so this skips request()'s response.json().
    const response = await fetch(`/api/applicants/${id}/attachments/${attachmentId}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${session.token()}` } })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
  },
  downloadCv: (id: number, filename: string) => download(`/api/applicants/${id}/cv`, filename),
  downloadAttachment: (a: Attachment) => download(`/api/applicants/${a.applicant_id}/attachments/${a.id}`, a.filename),
}

// File links need the token too, so download through fetch instead of a plain <a href>.
async function download(path: string, filename: string) {
  const response = await fetch(path, { headers: { Authorization: `Bearer ${session.token()}` } })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  const url = URL.createObjectURL(await response.blob())
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  link.click()
  URL.revokeObjectURL(url)
}

export function formatWhen(iso: string) {
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
