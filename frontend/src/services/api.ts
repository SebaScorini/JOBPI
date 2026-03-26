import {
  CVJobMatch,
  CvAnalysisResponse,
  JobAnalysisRequest,
  JobAnalysisResponse,
  Recommendation,
  StoredCV,
} from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '');

class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      (data && typeof data.detail === 'string' && data.detail) ||
      `API error: ${response.status} ${response.statusText}`;
    throw new ApiError(message, response.status);
  }

  return data as T;
}

export const apiService = {
  async analyzeJob(request: JobAnalysisRequest): Promise<JobAnalysisResponse> {
    const response = await fetch(`${API_BASE_URL}/jobs/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(request),
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<JobAnalysisResponse>(response);
  },

  async analyzeFit(title: string, description: string, cvFile: File): Promise<CvAnalysisResponse> {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('cv', cvFile);

    const response = await fetch(`${API_BASE_URL}/cv/analyze`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<CvAnalysisResponse>(response);
  },

  async listCVs(): Promise<StoredCV[]> {
    const response = await fetch(`${API_BASE_URL}/library/cvs`, {
      credentials: 'include',
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<StoredCV[]>(response);
  },

  async uploadCV(name: string, file: File): Promise<StoredCV> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/library/cvs`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<StoredCV>(response);
  },

  async deleteCV(cvId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/library/cvs/${cvId}`, {
      method: 'DELETE',
      credentials: 'include',
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    await parseResponse<{ ok: boolean }>(response);
  },

  async matchCVToJob(cvId: number, jobId: number): Promise<CVJobMatch> {
    const response = await fetch(`${API_BASE_URL}/library/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ cv_id: cvId, job_id: jobId }),
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<CVJobMatch>(response);
  },

  async recommendBestCV(jobId: number): Promise<Recommendation> {
    const response = await fetch(`${API_BASE_URL}/library/recommend/${jobId}`, {
      credentials: 'include',
    }).catch(() => {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    });

    return parseResponse<Recommendation>(response);
  },
};
