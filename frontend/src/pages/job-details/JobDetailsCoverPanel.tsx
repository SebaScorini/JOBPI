import { Check, Copy } from 'lucide-react';
import type { StoredCV } from '../../types';

interface JobDetailsCoverPanelProps {
  cvs: StoredCV[];
  selectedCvId: number | '';
  setSelectedCvId: (value: number) => void;
  isCoverLetterLoading: boolean;
  handleGenerateCoverLetter: () => void;
  coverLetter: string;
  copiedSection: 'cover' | 'match' | 'comparison' | null;
  handleCopyText: (text: string, section: 'cover' | 'match' | 'comparison') => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export function JobDetailsCoverPanel({
  cvs,
  selectedCvId,
  setSelectedCvId,
  isCoverLetterLoading,
  handleGenerateCoverLetter,
  coverLetter,
  copiedSection,
  handleCopyText,
  t,
}: JobDetailsCoverPanelProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-4 rounded-2xl border border-slate-200/70 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/20">
        <div>
          <label className="mb-2 block text-xs font-semibold uppercase text-slate-500">{t('jobDetails.targetCv')}</label>
          <select
            value={selectedCvId}
            onChange={(e) => setSelectedCvId(Number(e.target.value))}
            className="input-field !py-2.5 text-sm"
            disabled={cvs.length === 0}
          >
            <option value="" disabled>{t('common.selectCv')}</option>
            {cvs.map((cv) => <option key={cv.id} value={cv.id}>{cv.name}</option>)}
          </select>
        </div>

        <button
          onClick={handleGenerateCoverLetter}
          disabled={isCoverLetterLoading || !selectedCvId}
          className="btn-primary w-full px-6 !py-2.5 text-sm sm:w-auto"
        >
          {isCoverLetterLoading ? t('jobDetails.generating') : t('jobDetails.generateCoverLetter')}
        </button>
      </div>

      {coverLetter && (
        <div className="rounded-2xl border border-slate-200/70 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
          <pre className="max-h-[min(65vh,48rem)] overflow-y-auto whitespace-pre-wrap break-words pr-1 font-sans text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {coverLetter}
          </pre>
          <button onClick={() => handleCopyText(coverLetter, 'cover')} className="btn-secondary mt-3 flex w-full items-center justify-center gap-2 px-6 !py-2.5 text-sm sm:w-auto">
            {copiedSection === 'cover' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
          </button>
        </div>
      )}
    </div>
  );
}
