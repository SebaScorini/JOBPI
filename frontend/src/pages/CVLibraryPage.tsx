import React, { useEffect, useRef, useState } from 'react';
import { apiService } from '../services/api';
import { StoredCV } from '../types';
import {
  FileText,
  Loader2,
  UploadCloud,
  Trash2,
  Calendar,
  CheckCircle,
  AlertCircle,
  X,
  Tag,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function CVLibraryPage() {
  const { t, language } = useLanguage();
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<UploadFile[]>([]);
  const [tagInputs, setTagInputs] = useState<Record<number, string>>({});
  const [savingTagCvId, setSavingTagCvId] = useState<number | null>(null);
  const [activeTagFilter, setActiveTagFilter] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadCVs();
  }, []);

  useEffect(() => {
    if (selectedCvId && !cvs.some((cv) => cv.id === selectedCvId)) {
      setSelectedCvId(cvs[0]?.id ?? null);
    }
    if (!selectedCvId && cvs.length > 0) {
      setSelectedCvId(cvs[0].id);
    }
  }, [cvs, selectedCvId]);

  const loadCVs = async () => {
    try {
      const data = await apiService.listCVs();
      setCvs(data);
      setTagInputs(
        data.reduce((acc, cv) => {
          acc[cv.id] = cv.tags.join(', ');
          return acc;
        }, {} as Record<number, string>),
      );
    } catch (err) {
      console.error('Failed to load CVs', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    const newFiles: UploadFile[] = files.map((file) => ({
      file,
      status: 'pending',
    }));
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const removeSelectedFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleBatchUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setSelectedFiles((prev) => prev.map((file) => ({ ...file, status: 'uploading' as const })));

    try {
      const result = await apiService.batchUploadCVs(selectedFiles.map((file) => file.file));
      const resultsMap = result.results.reduce(
        (acc, item) => {
          acc[item.filename] = item;
          return acc;
        },
        {} as Record<string, { success: boolean; error?: string }>,
      );

      setSelectedFiles((prev) =>
        prev.map((file) => {
          const uploadResult = resultsMap[file.file.name];
          return {
            ...file,
            status: uploadResult?.success ? 'success' : 'error',
            error: uploadResult?.error,
          };
        }),
      );

      await loadCVs();

      window.setTimeout(() => {
        setSelectedFiles((prev) => prev.filter((file) => file.status === 'error'));
      }, 1800);
    } catch (err) {
      console.error('Failed to upload CVs', err);
      setSelectedFiles((prev) =>
        prev.map((file) => ({
          ...file,
          status: 'error',
          error: t('library.uploadFailed'),
        })),
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (cvId: number) => {
    if (!window.confirm(t('common.confirmDeleteCv'))) return;

    try {
      await apiService.deleteCV(cvId);
      setCvs((prev) => prev.filter((cv) => cv.id !== cvId));
    } catch (err) {
      console.error('Failed to delete CV', err);
    }
  };

  const handleSaveTags = async (cvId: number) => {
    const rawValue = tagInputs[cvId] ?? '';
    const tags = rawValue
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);

    setSavingTagCvId(cvId);
    try {
      const updatedCv = await apiService.updateCVTags(cvId, tags);
      setCvs((prev) => prev.map((cv) => (cv.id === cvId ? updatedCv : cv)));
      setTagInputs((prev) => ({ ...prev, [cvId]: updatedCv.tags.join(', ') }));

      if (activeTagFilter && !updatedCv.tags.includes(activeTagFilter)) {
        setActiveTagFilter('');
      }
    } catch (err) {
      console.error('Failed to update CV tags', err);
    } finally {
      setSavingTagCvId(null);
    }
  };

  const availableTags = Array.from(new Set(cvs.flatMap((cv) => cv.tags))).sort((a, b) =>
    a.localeCompare(b),
  );
  const visibleCvs = activeTagFilter ? cvs.filter((cv) => cv.tags.includes(activeTagFilter)) : cvs;
  const activeCv = visibleCvs.find((cv) => cv.id === selectedCvId) ?? visibleCvs[0] ?? null;

  return (
    <div className="space-y-4 animate-in fade-in duration-300 h-full">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('library.title')}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">{t('library.subtitle')}</p>
        </div>

        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept="application/pdf"
            className="hidden"
          />
          <button
            onClick={handleUploadClick}
            disabled={isUploading}
            className="btn-primary flex items-center justify-center gap-2 w-auto px-4 h-10 text-xs sm:text-sm"
          >
            {isUploading ? <Loader2 size={16} className="animate-spin" /> : <UploadCloud size={16} />}
            {t('library.uploadResumes')}
          </button>
        </div>
      </div>

      {selectedFiles.length > 0 && (
        <div className="glass-card-solid p-3 rounded-2xl space-y-3">
          <div className="space-y-2 max-h-44 overflow-y-auto">
            {selectedFiles.map((item, index) => (
              <div
                key={`${item.file.name}-${index}`}
                className={`flex items-center justify-between p-2 rounded-lg border ${
                  item.status === 'success'
                    ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30'
                    : item.status === 'error'
                      ? 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30'
                      : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText size={16} className="shrink-0" />
                  <span className="text-xs font-medium break-all">{item.file.name}</span>
                </div>

                <div className="flex items-center gap-1">
                  {item.status === 'uploading' && <Loader2 size={16} className="animate-spin text-brand-primary" />}
                  {item.status === 'success' && <CheckCircle size={16} className="text-emerald-500" />}
                  {item.status === 'error' && <AlertCircle size={16} className="text-rose-500" />}
                  {item.status === 'pending' && !isUploading && (
                    <button onClick={() => removeSelectedFile(index)} className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded">
                      <X size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {selectedFiles.some((file) => file.status === 'pending' || file.status === 'error') && !isUploading && (
            <button onClick={handleBatchUpload} className="btn-primary !py-2 text-sm">
              {t('library.uploadFiles', {
                count: selectedFiles.filter((file) => file.status === 'pending').length,
              })}
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4 min-h-[560px]">
        <aside className="glass-card p-3 rounded-2xl flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Tag size={14} />
              <span>{t('library.filterByTag')}</span>
            </div>
            <span className="text-xs text-slate-500">{visibleCvs.length}</span>
          </div>

          <div className="flex flex-wrap gap-1.5 mb-3">
            <button
              onClick={() => setActiveTagFilter('')}
              className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                activeTagFilter === ''
                  ? 'bg-brand-primary text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              {t('common.all')}
            </button>
            {availableTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setActiveTagFilter(tag)}
                className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                  activeTagFilter === tag
                    ? 'bg-brand-primary text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="animate-spin text-brand-primary h-6 w-6" />
              </div>
            ) : visibleCvs.length === 0 ? (
              <p className="text-xs text-slate-500 p-2">{cvs.length === 0 ? t('library.emptyLibrary') : t('library.noTagMatches')}</p>
            ) : (
              visibleCvs.map((cv) => (
                <button
                  key={cv.id}
                  onClick={() => setSelectedCvId(cv.id)}
                  className={`w-full text-left rounded-xl px-3 py-2 border transition-colors ${
                    activeCv?.id === cv.id
                      ? 'border-brand-primary bg-brand-primary/10'
                      : 'border-slate-200 bg-white/70 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/30 dark:hover:border-slate-700'
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 break-words">{cv.name}</p>
                  <p
                    className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400"
                    style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {cv.library_summary}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">{new Date(cv.created_at).toLocaleDateString(language)}</p>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="glass-card p-4 rounded-2xl min-h-0">
          {!activeCv ? (
            <div className="h-full flex items-center justify-center text-center border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl">
              <div>
                <FileText size={32} className="mx-auto text-slate-400 mb-3" />
                <p className="text-sm text-slate-500">{t('library.emptyLibraryDesc')}</p>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col gap-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-heading font-bold text-brand-text dark:text-white">{activeCv.name}</h2>
                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1"><Calendar size={12} /> {new Date(activeCv.created_at).toLocaleDateString(language)}</p>
                </div>
                <button
                  onClick={() => handleDelete(activeCv.id)}
                  className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300"
                >
                  <Trash2 size={14} />
                  {t('common.delete')}
                </button>
              </div>

              <div className="rounded-xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Summary</h3>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{activeCv.library_summary}</p>
              </div>

              <div className="rounded-xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4 space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{t('library.tags')}</h3>

                <div className="flex flex-wrap gap-2">
                  {activeCv.tags.length > 0 ? (
                    activeCv.tags.map((tag) => (
                      <span key={tag} className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400">{t('library.noTagsYet')}</span>
                  )}
                </div>

                <input
                  type="text"
                  value={tagInputs[activeCv.id] ?? ''}
                  onChange={(e) => setTagInputs((prev) => ({ ...prev, [activeCv.id]: e.target.value }))}
                  placeholder={t('library.tagsPlaceholder')}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                />

                <button
                  onClick={() => handleSaveTags(activeCv.id)}
                  disabled={savingTagCvId === activeCv.id}
                  className="btn-secondary w-full sm:w-auto px-5 !py-2 text-sm disabled:opacity-60"
                >
                  {savingTagCvId === activeCv.id ? t('common.saving') : t('library.saveTags')}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
