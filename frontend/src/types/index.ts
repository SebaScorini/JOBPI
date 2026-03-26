export interface JobAnalysisRequest {
  title: string;
  company: string;
  description: string;
}

export interface JobAnalysisResponse {
  job_id?: number | null;
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

export interface CvAnalysisResponse {
  fit_summary: string;
  strengths: string[];
  missing_skills: string[];
  likely_fit_level: 'Strong' | 'Moderate' | 'Weak' | string;
  resume_improvements: string[];
  interview_focus: string[];
  next_steps: string[];
}

export interface StoredCV {
  id: number;
  name: string;
  created_at: string;
}

export interface CVJobMatch {
  id: number;
  cv_id: number;
  job_id: number;
  heuristic_score: number;
  result: CvAnalysisResponse;
  created_at: string;
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
