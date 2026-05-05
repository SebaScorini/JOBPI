export type UILanguage = 'en' | 'es';
export type AIResponseLanguage = 'english' | 'spanish';

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
  language?: AIResponseLanguage;
}

export type JobApplicationStatus = 'saved' | 'applied' | 'interview' | 'rejected' | 'offer';
export type InterviewSessionType = 'mixed' | 'behavioral' | 'technical';
export type InterviewSessionStatus = 'in_progress' | 'completed';

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
  is_saved: boolean;
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
  ats_improvements: string[];
  recruiter_improvements: string[];
  rewritten_bullets: string[];
  interview_focus: string[];
  next_steps: string[];
}

export type MatchLevel = 'strong' | 'medium' | 'weak';

export interface StoredCV {
  id: number;
  name: string;
  summary: string;
  library_summary: string;
  has_file: boolean;
  is_favorite: boolean;
  tags: string[];
  created_at: string;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PaginatedResult<T> {
  items: T[];
  pagination: PaginationMeta;
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

export interface CVComparisonResult {
  winner: {
    cv_id: number;
    label: string;
  };
  overall_reason: string;
  comparative_strengths: string[];
  comparative_weaknesses: string[];
  job_alignment_breakdown: string[];
}

export interface CoverLetterResponse {
  generated_cover_letter: string;
}

export interface LinkedInProfileRequest {
  cv_id: number;
  job_ids?: number[];
  language?: AIResponseLanguage;
  regenerate?: boolean;
}

export interface LinkedInProfile {
  headline: string;
  about_summary: string;
  keywords: string[];
  optimization_tips: string[];
}

export interface ColdOutreachRequest {
  job_id: number;
  cv_id: number;
  hiring_manager_name?: string | null;
  language?: AIResponseLanguage;
  regenerate?: boolean;
}

export interface ColdOutreach {
  connection_message: string;
  personalization_notes: string[];
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

export interface InterviewQuestion {
  index: number;
  question: string;
  category: string;
  difficulty: string;
  rationale: string;
}

export interface InterviewAnswer {
  question_index: number;
  answer_text: string;
  answered_at: string;
}

export interface InterviewEvaluation {
  question_index: number;
  score: number;
  feedback: string;
  ideal_answer: string;
  improvement_tips: string[];
  evaluated_at: string;
}

export interface InterviewSessionSummary {
  focus_areas: string[];
  overall_score: number | null;
  strong_areas: string[];
  weak_areas: string[];
  next_steps: string[];
}

export interface InterviewSession {
  id: number;
  user_id: number;
  job_id: number;
  cv_id: number;
  session_type: InterviewSessionType;
  language: AIResponseLanguage;
  status: InterviewSessionStatus;
  questions: InterviewQuestion[];
  answers: InterviewAnswer[];
  evaluations: InterviewEvaluation[];
  summary: InterviewSessionSummary | null;
  current_question_index: number;
  next_question_index: number | null;
  is_complete: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface InterviewSessionCreate {
  cv_id: number;
  session_type: InterviewSessionType;
  language: AIResponseLanguage;
}

export interface InterviewAnswerSubmit {
  question_index: number;
  answer_text: string;
}

export interface InterviewFeedback extends InterviewEvaluation {
  session_id: number;
  answer_text: string;
  is_complete: boolean;
  next_question_index: number | null;
  summary: InterviewSessionSummary | null;
}
