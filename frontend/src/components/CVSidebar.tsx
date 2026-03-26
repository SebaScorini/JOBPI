import { useRef, useState } from 'react';
import { StoredCV } from '../types';

interface CVSidebarProps {
  cvs: StoredCV[];
  activeCvId: number | null;
  highlightedCvId: number | null;
  isLoading: boolean;
  isUploading: boolean;
  onSelect: (cv: StoredCV) => void;
  onUpload: (name: string, file: File) => Promise<void>;
  onDelete: (cvId: number) => Promise<void>;
}

export function CVSidebar({
  cvs,
  activeCvId,
  highlightedCvId,
  isLoading,
  isUploading,
  onSelect,
  onUpload,
  onDelete,
}: CVSidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !file) {
      return;
    }

    setError(null);
    try {
      await onUpload(name.trim(), file);
      setName('');
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not upload CV.');
    }
  };

  return (
    <aside className="glass-card rounded-3xl p-6 lg:col-span-3 h-fit sticky top-6">
      <div>
        <p className="text-[10px] font-bold tracking-widest uppercase text-slate-500 mb-1">CV Library</p>
        <h2 className="text-2xl font-black text-slate-900 dark:text-white">Saved resumes</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 font-medium leading-relaxed">
          Upload a PDF once and reuse it across every job analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-2xl border border-slate-200/60 dark:border-slate-800 bg-slate-50/50 dark:bg-[#0B0F19]/50 p-4 backdrop-blur-sm">
        <div>
          <label htmlFor="cv-library-name" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            CV name <span className="text-rose-500">*</span>
          </label>
          <input
            id="cv-library-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Senior Backend"
            className="input-field py-2.5"
          />
        </div>

        <div>
          <label htmlFor="cv-library-file" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            PDF file <span className="text-rose-500">*</span>
          </label>
          <input
            ref={fileInputRef}
            id="cv-library-file"
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 dark:text-slate-400 file:mr-3 file:rounded-full file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-slate-700 dark:file:text-slate-300 hover:file:bg-slate-300 dark:hover:file:bg-slate-700 cursor-pointer file:cursor-pointer transition-colors"
          />
          {file && <p className="mt-2 text-xs font-medium text-sky-600 dark:text-sky-400 truncate">{file.name}</p>}
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={isUploading || !name.trim() || !file}
            className="btn-primary"
          >
            {isUploading ? 'Saving CV...' : 'Upload New CV'}
          </button>
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}
      </form>

      <div className="mt-5 space-y-3">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 p-4">
            <div className="w-4 h-4 rounded-full border-2 border-slate-200 dark:border-slate-700 border-t-sky-500 animate-spin" />
            Loading saved CVs...
          </div>
        ) : cvs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 p-6 text-sm text-slate-500 dark:text-slate-400 text-center">
            <svg className="w-8 h-8 mx-auto mb-2 text-slate-400 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
            No CVs saved yet.
          </div>
        ) : (
          cvs.map((cv) => {
            const isActive = cv.id === activeCvId;
            const isHighlighted = cv.id === highlightedCvId;

            return (
              <button
                key={cv.id}
                type="button"
                onClick={() => onSelect(cv)}
                className={`w-full group rounded-2xl border p-4 text-left transition-all duration-300 ${
                  isActive
                    ? 'border-sky-500 bg-sky-50/50 dark:bg-sky-900/10 shadow-sm ring-1 ring-sky-500/20'
                    : 'border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-[#151B2B]/50 hover:border-sky-300 dark:hover:border-sky-700 hover:-translate-y-0.5'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className={`font-semibold ${isActive ? 'text-sky-900 dark:text-sky-400' : 'text-slate-900 dark:text-slate-200'}`}>{cv.name}</p>
                      {isHighlighted && (
                        <span className="rounded-full bg-emerald-100/80 dark:bg-emerald-500/10 border border-emerald-200/50 dark:border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-400 shadow-sm">
                          Star Pick
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-500">
                      Added {new Date(cv.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <span
                    role="button"
                    tabIndex={0}
                    onClick={async (event) => {
                      event.stopPropagation();
                      await onDelete(cv.id);
                    }}
                    onKeyDown={async (event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        event.stopPropagation();
                        await onDelete(cv.id);
                      }
                    }}
                    className="rounded-full p-2 text-slate-400 dark:text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-rose-600 dark:hover:text-rose-400"
                    aria-label={`Delete ${cv.name}`}
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18M8 6V4h8v2m-9 0 1 14h8l1-14" />
                    </svg>
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
