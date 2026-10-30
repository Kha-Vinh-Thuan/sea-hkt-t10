// Typed calls to the FastAPI backend (proxied at /api by Vite).

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

export type ApplicantDetail = Applicant & {
  cv_text: string
  activity: { id: number; message: string; created_at: string }[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
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

  jobs: () => request<Job[]>('/jobs'),
  createJob: (job: JobInput) => request<Job>('/jobs', json('POST', job)),
  stages: () => request<Stage[]>('/stages'),
  applicants: (jobId: number) => request<Applicant[]>(`/applicants?job_id=${jobId}`),
  applicant: (id: number) => request<ApplicantDetail>(`/applicants/${id}`),
  moveStage: (id: number, stage: Stage) => request<Applicant>(`/applicants/${id}/stage`, json('PATCH', { stage })),
  cvUrl: (id: number) => `/api/applicants/${id}/cv`,
}
