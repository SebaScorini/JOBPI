import {
  CoverLetterResponse,
  AIResponseLanguage,
  CVComparisonResult,
  CVJobMatch,
  CvAnalysisResponse,
  JobApplicationStatus,
  JobAnalysisRequest,
  JobAnalysisResponse,
  MatchLevel,
  StoredCV,
  TokenResponse,
  User,
} from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
const TOKEN_STORAGE_KEY = 'jobpi_token';

type ApiRequestOptions = Omit<RequestInit, 'headers'> & {
  headers?: HeadersInit;
  auth?: boolean;
  token?: string;
};

interface BackendUser {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

interface BackendJobAnalysisPayload {
  summary: string;
  seniority: string;
  role_type: string;
  required_skills: string[];
  nice_to_have_skills: string[];
  responsibilities: string[];
  how_to_prepare: string[];
  learning_path: string[];
  missing_skills: string[];
  resume_tips: string[];
  interview_tips: string[];
  portfolio_project_ideas: string[];
}

interface BackendJobRead {
  id: number;
  title: string;
  company: string;
  description: string;
  clean_description: string;
  analysis_result: BackendJobAnalysisPayload;
  status?: JobApplicationStatus;
  applied_date?: string | null;
  notes?: string | null;
  created_at: string | null;
}

interface BackendCVRead {
  id: number;
  filename: string;
  display_name: string;
  summary: string;
  tags: string[];
  created_at: string;
}

interface BackendMatchRead {
  id: number;
  user_id?: number;
  cv_id: number;
  job_id: number;
  match_level?: MatchLevel;
  fit_level?: string;
  fit_summary?: string;
  why_this_cv?: string;
  strengths?: string[];
  missing_skills?: string[];
  improvement_suggestions?: string[];
  suggested_improvements?: string[];
  missing_keywords?: string[];
  reorder_suggestions?: string[] | null;
  heuristic_score?: number;
  result?: Partial<CvAnalysisResponse>;
  recommended?: boolean;
  created_at: string;
}

interface BackendCVComparisonResponse {
  better_cv: {
    cv_id: number;
    label: string;
  };
  explanation: string;
  strengths_a: string[];
  strengths_b: string[];
}

class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function buildHeaders(options: ApiRequestOptions): HeadersInit {
  const headers = new Headers(options.headers ?? {});
  const token = options.token ?? getStoredToken();

  if (options.auth && token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return headers;
}

async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { auth = false, token, headers, ...init } = options;

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: buildHeaders({ ...init, auth, token, headers }),
    });

    return await parseResponse<T>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError('Could not connect to the API.');
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      (data && typeof data.detail === 'string' && data.detail) ||
      (data && Array.isArray(data.detail) && data.detail[0]?.msg) ||
      `API error: ${response.status} ${response.statusText}`;
    throw new ApiError(message, response.status);
  }

  return data as T;
}

function mapUser(user: BackendUser): User {
  return {
    id: user.id,
    email: user.email,
    is_active: user.is_active,
    created_at: user.created_at,
  };
}

function mapJob(job: BackendJobRead): JobAnalysisResponse {
  return {
    id: job.id,
    job_id: job.id,
    title: job.title,
    company: job.company,
    description: job.description,
    summary: job.analysis_result.summary,
    seniority: job.analysis_result.seniority,
    role_type: job.analysis_result.role_type,
    required_skills: job.analysis_result.required_skills,
    nice_to_have_skills: job.analysis_result.nice_to_have_skills,
    responsibilities: job.analysis_result.responsibilities,
    how_to_prepare: job.analysis_result.how_to_prepare,
    learning_path: job.analysis_result.learning_path,
    missing_skills: job.analysis_result.missing_skills,
    resume_tips: job.analysis_result.resume_tips,
    interview_tips: job.analysis_result.interview_tips,
    portfolio_project_ideas: job.analysis_result.portfolio_project_ideas,
    status: job.status ?? 'saved',
    applied_date: job.applied_date ?? null,
    notes: job.notes ?? null,
    created_at: job.created_at,
  };
}

function mapCV(cv: BackendCVRead): StoredCV {
  return {
    id: cv.id,
    name: cv.display_name,
    summary: cv.summary,
    tags: cv.tags ?? [],
    created_at: cv.created_at,
  };
}

function mapCvResult(match: BackendMatchRead): CvAnalysisResponse {
  return {
    fit_summary: match.result?.fit_summary ?? match.fit_summary ?? '',
    strengths: match.result?.strengths ?? match.strengths ?? [],
    missing_skills: match.result?.missing_skills ?? match.missing_skills ?? [],
    likely_fit_level: match.result?.likely_fit_level ?? match.fit_level ?? 'Unknown',
    resume_improvements: match.result?.resume_improvements ?? [],
    interview_focus: match.result?.interview_focus ?? [],
    next_steps: match.result?.next_steps ?? [],
  };
}

function deriveMatchLevel(match: BackendMatchRead): MatchLevel {
  if (match.match_level) {
    return match.match_level;
  }

  const fitLevel = (match.result?.likely_fit_level ?? match.fit_level ?? '').toLowerCase();
  if (fitLevel.includes('strong')) {
    return 'strong';
  }
  if (fitLevel.includes('moderate') || fitLevel.includes('medium')) {
    return 'medium';
  }
  if (fitLevel.includes('weak')) {
    return 'weak';
  }

  const score = match.heuristic_score ?? 0;
  if (score >= 0.5) {
    return 'strong';
  }
  if (score >= 0.25) {
    return 'medium';
  }
  return 'weak';
}

function mapMatch(match: BackendMatchRead): CVJobMatch {
  const result = mapCvResult(match);
  return {
    id: match.id,
    cv_id: match.cv_id,
    job_id: match.job_id,
    match_level: deriveMatchLevel(match),
    heuristic_score: match.heuristic_score ?? 0,
    why_this_cv: match.why_this_cv ?? result.fit_summary,
    strengths: match.strengths ?? result.strengths ?? [],
    missing_skills: match.missing_skills ?? result.missing_skills ?? [],
    improvement_suggestions: match.improvement_suggestions ?? result.resume_improvements ?? [],
    suggested_improvements: match.suggested_improvements ?? match.improvement_suggestions ?? result.resume_improvements ?? [],
    missing_keywords: match.missing_keywords ?? match.missing_skills ?? result.missing_skills ?? [],
    reorder_suggestions: match.reorder_suggestions ?? null,
    result,
    created_at: match.created_at,
    recommended: Boolean(match.recommended),
  };
}

export const authStorage = {
  getToken: getStoredToken,
  setToken: storeToken,
  clearToken: clearStoredToken,
};

export const apiService = {
  async register(email: string, password: string): Promise<User> {
    const user = await request<BackendUser>('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    return mapUser(user);
  },

  async login(username: string, password: string): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    return request<TokenResponse>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
  },

  async getMe(token?: string): Promise<User> {
    const user = await request<BackendUser>('/auth/me', {
      auth: true,
      token,
    });

    return mapUser(user);
  },

  async analyzeJob(requestBody: JobAnalysisRequest): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>('/jobs/analyze', {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    return mapJob(job);
  },

  async listJobs(): Promise<JobAnalysisResponse[]> {
    const jobs = await request<BackendJobRead[]>('/jobs', { auth: true });
    return jobs.map(mapJob);
  },

  async getJob(jobId: number): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>(`/jobs/${jobId}`, { auth: true });
    return mapJob(job);
  },

  async updateJobStatus(jobId: number, status: JobApplicationStatus, appliedDate?: string | null): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>(`/jobs/${jobId}/status`, {
      method: 'PATCH',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, ...(appliedDate ? { applied_date: appliedDate } : {}) }),
    });

    return mapJob(job);
  },

  async updateJobNotes(jobId: number, notes: string | null): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>(`/jobs/${jobId}/notes`, {
      method: 'PATCH',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });

    return mapJob(job);
  },

  async uploadCV(name: string, file: File): Promise<StoredCV> {
    const formData = new FormData();
    formData.append('display_name', name);
    formData.append('file', file);

    const cv = await request<BackendCVRead>('/cvs/upload', {
      method: 'POST',
      auth: true,
      body: formData,
    });

    return mapCV(cv);
  },

  async batchUploadCVs(files: File[]): Promise<{ results: Array<{ filename: string; success: boolean; cv?: StoredCV; error?: string }>; summary: { succeeded: number; failed: number } }> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await request<any>('/cvs/batch-upload', {
      method: 'POST',
      auth: true,
      body: formData,
    });

    // Map the response, converting cv objects
    return {
      results: response.results.map((r: any) => ({
        filename: r.filename,
        success: r.success,
        cv: r.cv ? mapCV(r.cv) : undefined,
        error: r.error,
      })),
      summary: response.summary,
    };
  },

  async listCVs(): Promise<StoredCV[]> {
    const cvs = await request<BackendCVRead[]>('/cvs', { auth: true });
    return cvs.map(mapCV);
  },

  async getCV(cvId: number): Promise<StoredCV> {
    const cv = await request<BackendCVRead>(`/cvs/${cvId}`, { auth: true });
    return mapCV(cv);
  },

  async updateCVTags(cvId: number, tags: string[]): Promise<StoredCV> {
    const cv = await request<BackendCVRead>(`/cvs/${cvId}/tags`, {
      method: 'PATCH',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags }),
    });

    return mapCV(cv);
  },

  async deleteCV(cvId: number): Promise<void> {
    await request<{ ok: boolean }>(`/cvs/${cvId}`, {
      method: 'DELETE',
      auth: true,
    });
  },

  async matchCVToJob(jobId: number, cvId: number, language: AIResponseLanguage = 'english'): Promise<CVJobMatch> {
    const match = await request<BackendMatchRead>(`/jobs/${jobId}/match-cvs`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_id: cvId, language }),
    });

    return mapMatch(match);
  },

  async compareCVsForJob(
    jobId: number,
    cvIdA: number,
    cvIdB: number,
    language: AIResponseLanguage = 'english',
  ): Promise<CVComparisonResult> {
    return request<BackendCVComparisonResponse>(`/jobs/${jobId}/compare-cvs`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_id_a: cvIdA, cv_id_b: cvIdB, language }),
    });
  },

  async generateCoverLetter(
    jobId: number,
    selectedCvId: number,
    language: AIResponseLanguage = 'english',
  ): Promise<CoverLetterResponse> {
    return request<CoverLetterResponse>(`/jobs/${jobId}/cover-letter`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_cv_id: selectedCvId, language }),
    });
  },

  async listMatches(): Promise<CVJobMatch[]> {
    const matches = await request<BackendMatchRead[]>('/matches', { auth: true });
    return matches.map(mapMatch);
  },

  async getMatch(matchId: number): Promise<CVJobMatch> {
    const match = await request<BackendMatchRead>(`/matches/${matchId}`, { auth: true });
    return mapMatch(match);
  },
};
