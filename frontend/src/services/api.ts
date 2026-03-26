import { CvAnalysisResponse, JobAnalysisRequest, JobAnalysisResponse } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '');

class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiService = {
  async analyzeJob(request: JobAnalysisRequest): Promise<JobAnalysisResponse> {
    let response: Response;

    try {
      response = await fetch(`${API_BASE_URL}/analyze-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(request),
      });
    } catch {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const message =
        (data && typeof data.detail === 'string' && data.detail) ||
        `API error: ${response.status} ${response.statusText}`;
      throw new ApiError(message, response.status);
    }

    return data as JobAnalysisResponse;
  },

  async analyzeFit(
    title: string,
    description: string,
    cvFile: File,
  ): Promise<CvAnalysisResponse> {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('cv', cvFile);

    let response: Response;

    try {
      response = await fetch(`${API_BASE_URL}/analyze-fit`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
    } catch {
      throw new ApiError('Could not connect to the API. Check that the backend is running.');
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const message =
        (data && typeof data.detail === 'string' && data.detail) ||
        `API error: ${response.status} ${response.statusText}`;
      throw new ApiError(message, response.status);
    }

    return data as CvAnalysisResponse;
  },
};

