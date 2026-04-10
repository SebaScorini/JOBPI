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
  PaginatedResult,
  PaginationMeta,
  StoredCV,
  TokenResponse,
  User,
} from '../types';

function resolveApiBaseUrl(): string {
  const apiBaseUrl = import.meta.env.VITE_API_URL?.trim();

  if (apiBaseUrl) {
    return apiBaseUrl.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const { hostname, origin } = window.location;
    const normalizedHostname = hostname.toLowerCase();

    if (normalizedHostname === 'localhost' || normalizedHostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }

    if (normalizedHostname === 'jobpi-api.vercel.app') {
      return origin.replace(/\/+$/, '');
    }

    return 'https://jobpi-api.vercel.app';
  }

  throw new Error('VITE_API_URL is not configured.');
}

const API_BASE_URL = resolveApiBaseUrl();
const TOKEN_STORAGE_KEY = 'jobpi_token';
const FRIENDLY_ERROR_MESSAGES: Record<string, string> = {
  ERR_RATE_LIMIT: "You're moving fast! Please wait a moment before trying again.",
  ERR_AI_TIMEOUT: 'Our AI is taking longer than expected. Please try again in a minute.',
  ERR_CV_NOT_FOUND: 'CV not found. It may have been deleted.',
  ERR_JOB_NOT_FOUND: 'Job not found. It may have been removed.',
  ERR_MATCH_NOT_FOUND: 'Match not found.',
  ERR_PAYLOAD_TOO_LARGE: 'That file or request is too large.',
  ERR_VALIDATION: 'Please review the highlighted inputs and try again.',
  ERR_SERVICE_UNAVAILABLE: 'This service is temporarily unavailable. Please try again.',
  ERR_UNAUTHORIZED: 'Your session expired. Please sign in again.',
  ERR_FORBIDDEN: 'You do not have permission to perform this action.',
  ERR_PDF_INVALID: "This file doesn't look like a valid PDF. Please try a different file.",
  ERR_CIRCUIT_BREAKER_OPEN: 'Our analysis service is temporarily busy. Please try again shortly.',
};

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
  is_saved?: boolean;
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
  library_summary: string;
  is_favorite?: boolean;
  tags: string[];
  created_at: string;
}

interface BackendCVListResponse {
  items: BackendCVRead[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface BackendJobListResponse {
  items: BackendJobRead[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface BackendMatchListResponse {
  items: BackendMatchRead[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
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

interface RegenerateOption {
  regenerate?: boolean;
}

interface DeleteSuccessResponse {
  success: boolean;
}

interface PaginationQuery {
  limit?: number;
  offset?: number;
}

interface CVListQuery extends PaginationQuery {
  search?: string;
  tags?: string[];
}

interface JobListQuery extends PaginationQuery {
  saved?: boolean;
}

interface BackendCVComparisonResponse {
  winner: {
    cv_id: number;
    label: string;
  };
  overall_reason: string;
  comparative_strengths: string[];
  comparative_weaknesses: string[];
  job_alignment_breakdown: string[];
}

interface BackendErrorResponse {
  error?: {
    code?: string;
    message?: string;
  };
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
    public readonly details?: Array<{ loc?: Array<string | number>; msg?: string }>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
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
  const data = (await response.json().catch(() => null)) as BackendErrorResponse | null;

  if (!response.ok) {
    const code = data?.error?.code;
    const details = Array.isArray(data?.detail) ? data.detail : undefined;
    const rawMessage =
      (data && typeof data.error?.message === 'string' && data.error.message) ||
      (data && typeof data.detail === 'string' && data.detail) ||
      details?.[0]?.msg ||
      `API error: ${response.status} ${response.statusText}`;
    const message = (code && FRIENDLY_ERROR_MESSAGES[code]) || rawMessage;
    throw new ApiError(message, response.status, code, details);
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
    is_saved: Boolean(job.is_saved),
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
    library_summary: cv.library_summary || cv.summary,
    is_favorite: Boolean(cv.is_favorite),
    tags: cv.tags ?? [],
    created_at: cv.created_at,
  };
}

function normalizeCVListResponse(payload: BackendCVRead[] | BackendCVListResponse): BackendCVRead[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  return Array.isArray(payload.items) ? payload.items : [];
}

function normalizeJobListResponse(payload: BackendJobRead[] | BackendJobListResponse): BackendJobRead[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  return Array.isArray(payload.items) ? payload.items : [];
}

function normalizeMatchListResponse(payload: BackendMatchRead[] | BackendMatchListResponse): BackendMatchRead[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  return Array.isArray(payload.items) ? payload.items : [];
}

function normalizePaginationMeta(
  payload: BackendCVRead[] | BackendJobRead[] | BackendMatchRead[] | BackendCVListResponse | BackendJobListResponse | BackendMatchListResponse,
  itemCount: number,
  fallbackLimit?: number,
  fallbackOffset?: number,
): PaginationMeta {
  if (Array.isArray(payload)) {
    const limit = fallbackLimit ?? payload.length;
    const offset = fallbackOffset ?? 0;
    return {
      total: payload.length,
      limit,
      offset,
      has_more: offset + itemCount < payload.length,
    };
  }

  const pagination = payload.pagination;
  return {
    total: pagination?.total ?? itemCount,
    limit: pagination?.limit ?? fallbackLimit ?? itemCount,
    offset: pagination?.offset ?? fallbackOffset ?? 0,
    has_more: Boolean(pagination?.has_more),
  };
}

function buildQueryString(params: PaginationQuery | CVListQuery): string {
  const searchParams = new URLSearchParams();

  Object.entries(params as Record<string, string | number | undefined | string[]>).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry) {
          searchParams.append(key, entry);
        }
      });
      return;
    }

    searchParams.set(key, String(value));
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
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
    const response = await this.listJobsPage();
    return response.items;
  },

  async listJobsPage(params: JobListQuery = {}): Promise<PaginatedResult<JobAnalysisResponse>> {
    const response = await request<BackendJobRead[] | BackendJobListResponse>(
      `/jobs${buildQueryString(params)}`,
      { auth: true },
    );
    const jobs = normalizeJobListResponse(response);
    return {
      items: jobs.map(mapJob),
      pagination: normalizePaginationMeta(response, jobs.length, params.limit, params.offset),
    };
  },

  async getJob(jobId: number): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>(`/jobs/${jobId}`, { auth: true });
    return mapJob(job);
  },

  async toggleSavedJob(jobId: number): Promise<JobAnalysisResponse> {
    const job = await request<BackendJobRead>(`/jobs/${jobId}/toggle-saved`, {
      method: 'PATCH',
      auth: true,
    });

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

  async deleteJob(jobId: number): Promise<boolean> {
    const response = await request<DeleteSuccessResponse>(`/jobs/${jobId}`, {
      method: 'DELETE',
      auth: true,
    });

    return response.success;
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
    const response = await this.listCVsPage();
    return response.items;
  },

  async listCVsPage(params: CVListQuery = {}): Promise<PaginatedResult<StoredCV>> {
    const response = await request<BackendCVRead[] | BackendCVListResponse>(
      `/cvs${buildQueryString(params)}`,
      { auth: true },
    );
    const cvs = normalizeCVListResponse(response);
    return {
      items: cvs.map(mapCV),
      pagination: normalizePaginationMeta(response, cvs.length, params.limit, params.offset),
    };
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

  async toggleFavoriteCV(cvId: number): Promise<StoredCV> {
    const cv = await request<BackendCVRead>(`/cvs/${cvId}/toggle-favorite`, {
      method: 'PATCH',
      auth: true,
    });

    return mapCV(cv);
  },

  async deleteCV(cvId: number): Promise<void> {
    await request<{ ok: boolean }>(`/cvs/${cvId}`, {
      method: 'DELETE',
      auth: true,
    });
  },

  async bulkDeleteCVs(cvIds: number[]): Promise<{ deleted: number; failed: number; updated: number }> {
    return request<{ deleted: number; failed: number; updated: number }>('/cvs/bulk-delete', {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_ids: cvIds }),
    });
  },

  async bulkTagCVs(cvIds: number[], tags: string[]): Promise<{ deleted: number; failed: number; updated: number }> {
    return request<{ deleted: number; failed: number; updated: number }>('/cvs/bulk-tag', {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_ids: cvIds, tags }),
    });
  },

  async matchCVToJob(
    jobId: number,
    cvId: number,
    language: AIResponseLanguage = 'english',
    options: RegenerateOption = {},
  ): Promise<CVJobMatch> {
    const match = await request<BackendMatchRead>(`/jobs/${jobId}/match-cvs`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_id: cvId, language, regenerate: options.regenerate ?? false }),
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
    options: RegenerateOption = {},
  ): Promise<CoverLetterResponse> {
    return request<CoverLetterResponse>(`/jobs/${jobId}/cover-letter`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_cv_id: selectedCvId,
        language,
        regenerate: options.regenerate ?? false,
      }),
    });
  },

  async listMatches(): Promise<CVJobMatch[]> {
    const response = await this.listMatchesPage();
    return response.items;
  },

  async listMatchesPage(params: PaginationQuery = {}): Promise<PaginatedResult<CVJobMatch>> {
    const response = await request<BackendMatchRead[] | BackendMatchListResponse>(
      `/matches${buildQueryString(params)}`,
      { auth: true },
    );
    const matches = normalizeMatchListResponse(response);
    return {
      items: matches.map(mapMatch),
      pagination: normalizePaginationMeta(response, matches.length, params.limit, params.offset),
    };
  },

  async getMatch(matchId: number): Promise<CVJobMatch> {
    const match = await request<BackendMatchRead>(`/matches/${matchId}`, { auth: true });
    return mapMatch(match);
  },
};
