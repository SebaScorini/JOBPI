import { useState } from 'react';
import { JobForm } from './components/JobForm';
import { ResultCard } from './components/ResultCard';
import { CvForm } from './components/CvForm';
import { CvResultCard } from './components/CvResultCard';
import { apiService } from './services/api';
import { CvAnalysisResponse, JobAnalysisRequest, JobAnalysisResponse } from './types';

type Tab = 'job' | 'cv';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('job');

  // Job analyzer state
  const [jobLoading, setJobLoading] = useState(false);
  const [jobResult, setJobResult] = useState<JobAnalysisResponse | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  // CV fit state
  const [cvLoading, setCvLoading] = useState(false);
  const [cvResult, setCvResult] = useState<CvAnalysisResponse | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  const handleAnalyzeJob = async (data: JobAnalysisRequest) => {
    setJobLoading(true);
    setJobError(null);
    setJobResult(null);
    try {
      const response = await apiService.analyzeJob(data);
      setJobResult(response);
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setJobLoading(false);
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

  const isLoading = activeTab === 'job' ? jobLoading : cvLoading;
  const error = activeTab === 'job' ? jobError : cvError;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-blue-200">
      <div className="max-w-5xl mx-auto px-4 py-12 md:py-20">

        {/* Header */}
        <header className="mb-10 text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center justify-center p-3 bg-blue-600 rounded-2xl shadow-lg mb-6">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 mb-4">AI Job Analyzer</h1>
          <p className="text-lg text-gray-600">
            Analyze any job description — or upload your CV to check your fit.
          </p>
        </header>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-xl mb-10 max-w-sm mx-auto">
          {(['job', 'cv'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab
                  ? 'bg-white shadow text-gray-900'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'job' ? '📋 Job Analyzer' : '📄 CV Fit'}
            </button>
          ))}
        </div>

        {/* Main Content Grid */}
        <main className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

          {/* Left — Form */}
          <div className="lg:col-span-5 w-full">
            {activeTab === 'job' ? (
              <JobForm onSubmit={handleAnalyzeJob} isLoading={jobLoading} />
            ) : (
              <CvForm onSubmit={handleAnalyzeFit} isLoading={cvLoading} />
            )}
          </div>

          {/* Right — Results */}
          <div className="lg:col-span-7 w-full">
            {error && (
              <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl p-6 mb-6">
                <h3 className="text-lg font-semibold mb-2 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  Analysis Failed
                </h3>
                <p>{error}</p>
              </div>
            )}

            {activeTab === 'job' && jobResult && <ResultCard result={jobResult} />}
            {activeTab === 'cv' && cvResult && <CvResultCard result={cvResult} />}

            {!isLoading && !error && (
              (activeTab === 'job' && !jobResult) || (activeTab === 'cv' && !cvResult)
            ) && (
              <div className="bg-white border border-dashed border-gray-300 rounded-xl p-12 text-center text-gray-500 flex flex-col items-center justify-center min-h-[300px]">
                <svg className="w-12 h-12 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium text-gray-700 mb-1">No results yet</p>
                <p className="text-sm">Fill in the form and hit analyze to see results here.</p>
              </div>
            )}

            {isLoading && (
              <div className="bg-white border border-gray-100 shadow-sm rounded-xl p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
                <div className="animate-pulse flex flex-col items-center">
                  <div className="h-12 w-12 bg-blue-100 rounded-full mb-4 flex items-center justify-center">
                    <svg className="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-700 mb-2">
                    {activeTab === 'job' ? 'Analyzing Job Description...' : 'Analyzing CV Fit...'}
                  </p>
                  <p className="text-gray-500">This may take up to 60 seconds</p>
                </div>
              </div>
            )}
          </div>

        </main>
      </div>
    </div>
  );
}

export default App;
