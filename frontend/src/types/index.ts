export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface JobAnalysisRequest {
  title: string;
  company: string;
  description: string;
}

export type JobApplicationStatus = 'saved' | 'applied' | 'interview' | 'rejected' | 'offer';

export interface JobAnalysisResponse {
  id: number;
  job_id: number;
  title: string;
  company: string;
  description: string;
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
  status: JobApplicationStatus;
  applied_date: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface CvAnalysisResponse {
  fit_summary: string;
  strengths: string[];
  missing_skills: string[];
  likely_fit_level: 'Strong' | 'Moderate' | 'Weak' | string;
  resume_improvements: string[];
  interview_focus: string[];
  next_steps: string[];
}

export type MatchLevel = 'strong' | 'medium' | 'weak';

export interface StoredCV {
  id: number;
  name: string;
  summary: string;
  created_at: string;
}

export interface CVJobMatch {
  id: number;
  cv_id: number;
  job_id: number;
  match_level: MatchLevel;
  heuristic_score: number;
  why_this_cv: string;
  strengths: string[];
  missing_skills: string[];
  improvement_suggestions: string[];
  suggested_improvements: string[];
  missing_keywords: string[];
  reorder_suggestions?: string[] | null;
  result: CvAnalysisResponse;
  created_at: string;
  recommended: boolean;
}

export interface RecommendationMatch {
  cv_id: number;
  score: number;
}

export interface Recommendation {
  best_cv: {
    id: number;
    name: string;
  };
  score: number;
  matches: RecommendationMatch[];
}
