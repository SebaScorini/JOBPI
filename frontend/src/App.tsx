import { useEffect, useState } from 'react';
import { CVSidebar } from './components/CVSidebar';
import { CvForm } from './components/CvForm';
import { CvResultCard } from './components/CvResultCard';
import { JobForm } from './components/JobForm';
import { AnalysisModal } from './components/AnalysisModal';
import { apiService } from './services/api';
import {
  CVJobMatch,
  CvAnalysisResponse,
  JobAnalysisRequest,
  JobAnalysisResponse,
  Recommendation,
  StoredCV,
} from './types';

function App() {
  const [activeView, setActiveView] = useState<'library' | 'adhoc'>('library');
  const [storedCVs, setStoredCVs] = useState<StoredCV[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [uploadingCV, setUploadingCV] = useState(false);
  const [activeCV, setActiveCV] = useState<StoredCV | null>(null);
  const [recommendedCVId, setRecommendedCVId] = useState<number | null>(null);

  const [jobLoading, setJobLoading] = useState(false);
  const [jobResult, setJobResult] = useState<JobAnalysisResponse | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  const [matchLoading, setMatchLoading] = useState(false);
  const [matchResult, setMatchResult] = useState<CVJobMatch | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);

  const [cvLoading, setCvLoading] = useState(false);
  const [cvResult, setCvResult] = useState<CvAnalysisResponse | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);

  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark') || window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  useEffect(() => {
    void loadStoredCVs();
  }, []);

  useEffect(() => {
    if (!activeCV || !jobResult?.job_id) {
      return;
    }

    void runMatch(activeCV.id, jobResult.job_id);
  }, [activeCV, jobResult?.job_id]);

  const loadStoredCVs = async () => {
    setLibraryLoading(true);
    try {
      const cvs = await apiService.listCVs();
      setStoredCVs(cvs);
      setActiveCV((current) => (current ? cvs.find((cv) => cv.id === current.id) ?? null : cvs[0] ?? null));
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Could not load saved CVs.');
    } finally {
      setLibraryLoading(false);
    }
  };

  const handleAnalyzeJob = async (data: JobAnalysisRequest) => {
    setJobLoading(true);
    setJobError(null);
    setJobResult(null);
    setMatchResult(null);
    setMatchError(null);
    setRecommendation(null);
    setRecommendedCVId(null);

    try {
      const response = await apiService.analyzeJob(data);
      setJobResult(response);
      setIsModalOpen(true);
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setJobLoading(false);
    }
  };

  const runMatch = async (cvId: number, jobId: number) => {
    setMatchLoading(true);
    setMatchError(null);
    try {
      const response = await apiService.matchCVToJob(cvId, jobId);
      setMatchResult(response);
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : 'Could not match CV to job.');
    } finally {
      setMatchLoading(false);
    }
  };

  const handleUploadCV = async (name: string, file: File) => {
    setUploadingCV(true);
    try {
      const created = await apiService.uploadCV(name, file);
      setStoredCVs((current) => [created, ...current]);
      setActiveCV(created);
    } finally {
      setUploadingCV(false);
    }
  };

  const handleDeleteCV = async (cvId: number) => {
    await apiService.deleteCV(cvId);
    setStoredCVs((current) => {
      const next = current.filter((cv) => cv.id !== cvId);
      if (activeCV?.id === cvId) {
        setActiveCV(next[0] ?? null);
        setMatchResult(null);
      }
      return next;
    });

    if (recommendedCVId === cvId) {
      setRecommendedCVId(null);
      setRecommendation(null);
    }
  };

  const handleRecommendBestCV = async () => {
    if (!jobResult?.job_id) {
      return;
    }

    setMatchError(null);
    try {
      const response = await apiService.recommendBestCV(jobResult.job_id);
      setRecommendation(response);
      setRecommendedCVId(response.best_cv.id);
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : 'Could not load recommendation.');
    }
  };

  const handleAnalyzeFit = async (title: string, description: string, cvFile: File) => {
    setCvLoading(true);
    setCvError(null);
    setCvResult(null);
    try {
      const response = await apiService.analyzeFit(title, description, cvFile);
      setCvResult(response);
    } catch (err) {
      setCvError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setCvLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 selection:bg-sky-200 dark:selection:bg-sky-900/50 transition-colors duration-500 relative">
      {/* Decorative gradient orb */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-500/10 dark:bg-sky-500/5 blur-[120px] rounded-full pointer-events-none transition-colors duration-500" />
      
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-12 relative z-10">
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="rounded-full bg-white/50 dark:bg-white/5 p-2.5 text-slate-500 dark:text-slate-400 hover:text-sky-600 dark:hover:text-sky-400 hover:bg-white dark:hover:bg-white/10 shadow-sm backdrop-blur-md transition-all ring-1 ring-slate-200/50 dark:ring-white/10"
            aria-label="Toggle dark mode"
          >
            {isDarkMode ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
            )}
          </button>
        </div>
        
        <header className="mb-8 max-w-3xl">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-sky-500 animate-pulse"></div>
            <p className="text-sm font-bold uppercase tracking-[0.28em] text-sky-600 dark:text-sky-400">JOBPI STUDIO</p>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white md:text-5xl lg:text-6xl pb-2">
            Target jobs with <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-indigo-500 dark:from-sky-400 dark:to-indigo-400">precision.</span>
          </h1>
          <p className="mt-4 text-lg text-slate-600 dark:text-slate-400 font-medium max-w-2xl leading-relaxed">
            Analyze roles, manage your resume library, and generate persistent actionable insights to land your next position.
          </p>
        </header>

        {/* VIEW TOGGLER */}
        <div className="flex items-center gap-2 p-1.5 bg-slate-200/50 dark:bg-slate-800/50 rounded-2xl w-fit mb-12 shadow-sm border border-slate-200/50 dark:border-slate-700/50">
           <button 
             onClick={() => setActiveView('library')} 
             className={`px-5 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center gap-2 ${activeView === 'library' ? 'bg-white dark:bg-slate-700 shadow-sm text-sky-600 dark:text-sky-400' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
           >
             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
             Library Engine
           </button>
           <button 
             onClick={() => setActiveView('adhoc')} 
             className={`px-5 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center gap-2 ${activeView === 'adhoc' ? 'bg-white dark:bg-slate-700 shadow-sm text-emerald-600 dark:text-emerald-400' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
           >
             <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
             Ad-Hoc Check
           </button>
        </div>

        {activeView === 'library' ? (
        <main className="flex flex-col xl:flex-row gap-8 lg:gap-12 animate-in fade-in duration-500">
          {/* LEFT SIDEBAR */}
          <div className="w-full xl:w-[340px] flex-shrink-0">
            <CVSidebar
              cvs={storedCVs}
              activeCvId={activeCV?.id ?? null}
              highlightedCvId={recommendedCVId}
              isLoading={libraryLoading}
              isUploading={uploadingCV}
              onSelect={setActiveCV}
              onUpload={handleUploadCV}
              onDelete={handleDeleteCV}
            />
          </div>

          {/* MAIN CONTENT */}
          <div className="flex-1 min-w-0 space-y-16 pb-20">
            
            {/* 1. JOB ENGINE */}
            <section className="space-y-6">
              <div className="flex items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-sky-100 dark:bg-sky-500/10 flex items-center justify-center text-sky-600 dark:text-sky-400">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">1. Target Job</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Input the job description you want to optimize for.</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6 md:p-8 rounded-3xl">
                <JobForm onSubmit={handleAnalyzeJob} isLoading={jobLoading} />
              </div>

              {jobError && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
                  {jobError}
                </div>
              )}

              {jobLoading ? (
                <div className="glass-card p-12 text-center rounded-3xl animate-pulse">
                  <div className="w-14 h-14 mx-auto mb-5 rounded-full border-4 border-slate-200 dark:border-slate-700 border-t-sky-500 animate-spin" />
                  <p className="text-xl font-bold text-slate-900 dark:text-white">Decoding job requirements...</p>
                  <p className="mt-2 text-slate-500 dark:text-slate-400 font-medium">Extracting core skills, responsibilities, and success metrics.</p>
                </div>
              ) : jobResult ? (
                <div className="glass-card flex items-center justify-between p-6 md:p-8 rounded-3xl mt-6 border-sky-200/50 dark:border-sky-800/30 bg-sky-50/50 dark:bg-sky-900/10 animate-in fade-in zoom-in-95 duration-300">
                  <div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                      Analysis Complete
                    </h3>
                    <p className="text-slate-500 dark:text-slate-400 font-medium text-sm md:text-base">Job requirements mapped and CV alignment calculated.</p>
                  </div>
                  <button 
                    onClick={() => setIsModalOpen(true)} 
                    className="btn-primary whitespace-nowrap py-3 px-6 shadow-md hover:shadow-lg transition-all"
                  >
                    Open Viewport
                  </button>
                </div>
              ) : null}
            </section>

          </div>
        </main>
        ) : (
        <main className="max-w-4xl pb-20 animate-in fade-in duration-500">
          <section className="space-y-6">
            <div className="flex items-center gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
              <div className="w-10 h-10 rounded-2xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Ad-Hoc Analysis</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">Quickly verify a PDF without saving it to your library.</p>
              </div>
            </div>

            <div className="glass-card p-6 md:p-8 rounded-3xl">
              <CvForm onSubmit={handleAnalyzeFit} isLoading={cvLoading} />
            </div>

            {cvError && (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
                {cvError}
              </div>
            )}

            {cvLoading ? (
              <div className="glass-card flex flex-col items-center justify-center p-12 mt-6 rounded-3xl animate-pulse">
                <div className="w-14 h-14 mx-auto mb-5 rounded-full border-4 border-slate-200 dark:border-slate-700 border-t-emerald-500 animate-spin" />
                <p className="text-xl font-bold text-slate-900 dark:text-white">Analyzing raw document fit...</p>
                <p className="mt-2 text-slate-500 dark:text-slate-400 font-medium">Evaluating contextual alignment against prompt.</p>
              </div>
            ) : cvResult ? (
              <div className="mt-6">
                <CvResultCard result={cvResult} />
              </div>
            ) : null}
          </section>
        </main>
        )}
      </div>
      
      <AnalysisModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        jobResult={jobResult}
        matchResult={matchResult}
        activeCv={activeCV}
        matchLoading={matchLoading}
        matchError={matchError}
        recommendation={recommendation}
        onRecommend={handleRecommendBestCV}
        isRecommended={activeCV?.id === recommendedCVId}
      />
    </div>
  );
}

export default App;
