import {
  CVJobMatch,
  CvAnalysisResponse,
  JobAnalysisRequest,
  JobAnalysisResponse,
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
  created_at: string | null;
}

interface BackendCVRead {
  id: number;
  filename: string;
  display_name: string;
  summary: string;
  created_at: string;
}

interface BackendMatchRead {
  id: number;
  user_id?: number;
  cv_id: number;
  job_id: number;
  fit_level?: string;
  fit_summary?: string;
  strengths?: string[];
  missing_skills?: string[];
  heuristic_score?: number;
  result?: Partial<CvAnalysisResponse>;
  recommended?: boolean;
  created_at: string;
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
    created_at: job.created_at,
  };
}

function mapCV(cv: BackendCVRead): StoredCV {
  return {
    id: cv.id,
    name: cv.display_name,
    summary: cv.summary,
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

function mapMatch(match: BackendMatchRead): CVJobMatch {
  return {
    id: match.id,
    cv_id: match.cv_id,
    job_id: match.job_id,
    heuristic_score: match.heuristic_score ?? 0,
    result: mapCvResult(match),
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

  async listCVs(): Promise<StoredCV[]> {
    const cvs = await request<BackendCVRead[]>('/cvs', { auth: true });
    return cvs.map(mapCV);
  },

  async getCV(cvId: number): Promise<StoredCV> {
    const cv = await request<BackendCVRead>(`/cvs/${cvId}`, { auth: true });
    return mapCV(cv);
  },

  async deleteCV(cvId: number): Promise<void> {
    await request<{ ok: boolean }>(`/cvs/${cvId}`, {
      method: 'DELETE',
      auth: true,
    });
  },

  async matchCVToJob(jobId: number, cvId: number): Promise<CVJobMatch> {
    const match = await request<BackendMatchRead>(`/jobs/${jobId}/match-cvs`, {
      method: 'POST',
      auth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_id: cvId }),
    });

    return mapMatch(match);
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
