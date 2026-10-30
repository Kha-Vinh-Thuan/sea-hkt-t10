// Typed calls to the FastAPI backend (proxied at /api by Vite). Recruiter calls carry the login token.

export type Stage = 'new' | 'screening' | 'interview' | 'offer' | 'hired' | 'rejected'

export const STAGE_LABEL: Record<Stage, string> = {
  new: 'New', screening: 'Screening', interview: 'Interview', offer: 'Offer', hired: 'Hired', rejected: 'Rejected',
}

export type PublicJob = {
  id: number
  title: string
  department: string
  location: string
  description: string
  requirements: string
}

export type Job = PublicJob & {
  interview_duration_minutes: number
  openings: number
  is_open: boolean
  applicant_count: number
}

export type JobInput = Omit<Job, 'id' | 'applicant_count'>

export type Applicant = {
  id: number
  job_id: number
  name: string
  email: string
  phone: string
  stage: Stage
  cv_filename: string
  created_at: string
}

export type Interview = {
  id: number
  applicant_id: number
  interviewer_name: string
  interviewer_email: string
  start: string
  end: string
  location: string
}

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
  stages: () => request<Stage[]>('/stages'),
  applicants: (jobId: number) => request<Applicant[]>(`/applicants?job_id=${jobId}`),
  applicant: (id: number) => request<ApplicantDetail>(`/applicants/${id}`),
  moveStage: (id: number, stage: Stage) => request<Applicant>(`/applicants/${id}/stage`, json('PATCH', { stage })),
  scheduleInterview: (id: number, data: InterviewInput) =>
    request<{ interview: Interview; emailed: boolean; mail_error: string | null }>(
      `/applicants/${id}/interviews`, json('POST', data)),
  interviews: () => request<UpcomingInterview[]>('/interviews'),

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
