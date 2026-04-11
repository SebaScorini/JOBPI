import React, { useEffect, useRef, useState } from 'react';
import { apiService } from '../services/api';
import { PaginationMeta, StoredCV } from '../types';
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
  Search,
  Star,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { validateUploadFiles } from '../utils/validation';
import { PaginationControls } from '../components/PaginationControls';

interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function CVLibraryPage() {
  const PAGE_SIZE = 20;
  const { t, language } = useLanguage();
  const { showToast } = useToast();
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | null>(null);
  const [selectedCvIds, setSelectedCvIds] = useState<number[]>([]);
  const [bulkTagInput, setBulkTagInput] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [isBulkTagging, setIsBulkTagging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<UploadFile[]>([]);
  const [tagInputs, setTagInputs] = useState<Record<number, string>>({});
  const [savingTagCvId, setSavingTagCvId] = useState<number | null>(null);
  const [togglingFavoriteCvId, setTogglingFavoriteCvId] = useState<number | null>(null);
  const [activeTagFilter, setActiveTagFilter] = useState<string>('');
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [pagination, setPagination] = useState<PaginationMeta>({
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
    has_more: false,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPagination((current) => ({ ...current, offset: 0 }));
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  useEffect(() => {
    loadCVs();
  }, [pagination.offset, searchQuery, activeTagFilter]);

  useEffect(() => {
    if (selectedCvId && !cvs.some((cv) => cv.id === selectedCvId)) {
      setSelectedCvId(cvs[0]?.id ?? null);
    }
    if (!selectedCvId && cvs.length > 0) {
      setSelectedCvId(cvs[0].id);
    }
  }, [cvs, selectedCvId]);

  useEffect(() => {
    setSelectedCvIds((current) => current.filter((cvId) => cvs.some((cv) => cv.id === cvId)));
  }, [cvs]);

  const loadCVs = async () => {
    try {
      const data = await apiService.listCVsPage({
        limit: PAGE_SIZE,
        offset: pagination.offset,
        search: searchQuery || undefined,
        tags: activeTagFilter ? [activeTagFilter] : undefined,
      });
      setCvs(data.items);
      setPagination(data.pagination);
      setTagInputs(
        data.items.reduce((acc, cv) => {
          acc[cv.id] = cv.tags.join(', ');
          return acc;
        }, {} as Record<number, string>),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedLoad');
      showToast(message, 'error');
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

    const validationError = validateUploadFiles(files);
    if (validationError) {
      showToast(validationError, 'error');
      return;
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

    const validationError = validateUploadFiles(selectedFiles.map((item) => item.file));
    if (validationError) {
      showToast(validationError, 'error');
      return;
    }

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
      showToast(
        result.summary.failed === 0
          ? t('library.uploadComplete')
          : t('library.uploadFinishedSummary', {
              succeeded: result.summary.succeeded,
              failed: result.summary.failed,
            }),
        result.summary.failed === 0 ? 'success' : 'warning',
      );

      window.setTimeout(() => {
        setSelectedFiles((prev) => prev.filter((file) => file.status === 'error'));
      }, 1800);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.uploadFailed');
      showToast(message, 'error');
      setSelectedFiles((prev) =>
        prev.map((file) => ({
          ...file,
          status: 'error',
          error: message,
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
      const nextOffset =
        cvs.length === 1 && pagination.offset > 0
          ? Math.max(0, pagination.offset - PAGE_SIZE)
          : pagination.offset;

      if (nextOffset !== pagination.offset) {
        setPagination((current) => ({ ...current, offset: nextOffset }));
      } else {
        setCvs((prev) => prev.filter((cv) => cv.id !== cvId));
        setPagination((current) => ({
          ...current,
          total: Math.max(0, current.total - 1),
          has_more: current.offset + current.limit < Math.max(0, current.total - 1),
        }));
      }
      showToast(t('library.deletedSuccess'), 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedDelete');
      showToast(message, 'error');
    }
  };

  const toggleCvSelection = (cvId: number) => {
    setSelectedCvIds((current) =>
      current.includes(cvId) ? current.filter((id) => id !== cvId) : [...current, cvId],
    );
  };

  const handleSelectAllVisible = () => {
    const visibleIds = visibleCvs.map((cv) => cv.id);
    const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((cvId) => selectedCvIds.includes(cvId));
    setSelectedCvIds((current) => {
      if (allVisibleSelected) {
        return current.filter((cvId) => !visibleIds.includes(cvId));
      }
      return Array.from(new Set([...current, ...visibleIds]));
    });
  };

  const handleBulkDelete = async () => {
    if (selectedCvIds.length === 0) {
      return;
    }
    if (!window.confirm(t('library.bulkDeleteConfirm'))) {
      return;
    }

    setIsBulkDeleting(true);
    try {
      const result = await apiService.bulkDeleteCVs(selectedCvIds);
      setSelectedCvIds([]);
      const remainingItems = cvs.filter((cv) => !selectedCvIds.includes(cv.id));
      const nextOffset =
        remainingItems.length === 0 && pagination.offset > 0
          ? Math.max(0, pagination.offset - PAGE_SIZE)
          : pagination.offset;

      if (nextOffset !== pagination.offset) {
        setPagination((current) => ({ ...current, offset: nextOffset }));
      } else {
        setCvs(remainingItems);
        setPagination((current) => ({
          ...current,
          total: Math.max(0, current.total - result.deleted),
          has_more: current.offset + current.limit < Math.max(0, current.total - result.deleted),
        }));
      }
      showToast(
        result.failed > 0
          ? t('library.bulkDeleteSummaryWithFailures', {
              deleted: result.deleted,
              failed: result.failed,
            })
          : t('library.bulkDeleteSummarySuccess', {
              deleted: result.deleted,
            }),
        result.failed > 0 ? 'warning' : 'success',
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedDelete');
      showToast(message, 'error');
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const handleBulkTag = async () => {
    const tags = bulkTagInput
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);

    if (selectedCvIds.length === 0 || tags.length === 0) {
      return;
    }

    setIsBulkTagging(true);
    try {
      const result = await apiService.bulkTagCVs(selectedCvIds, tags);
      setCvs((current) =>
        current.map((cv) => {
          if (!selectedCvIds.includes(cv.id)) {
            return cv;
          }

          const mergedTags = [...cv.tags];
          for (const tag of tags) {
            if (!mergedTags.includes(tag)) {
              mergedTags.push(tag);
            }
          }

          return { ...cv, tags: mergedTags };
        }),
      );
      setTagInputs((current) => {
        const next = { ...current };
        for (const cvId of selectedCvIds) {
          const existingTags = (next[cvId] ?? '')
            .split(',')
            .map((tag) => tag.trim())
            .filter(Boolean);
          const mergedTags = [...existingTags];
          for (const tag of tags) {
            if (!mergedTags.includes(tag)) {
              mergedTags.push(tag);
            }
          }
          next[cvId] = mergedTags.join(', ');
        }
        return next;
      });
      setBulkTagInput('');
      showToast(
        result.failed > 0
          ? t('library.bulkTagSummaryWithFailures', {
              updated: result.updated,
              failed: result.failed,
            })
          : t('library.bulkTagSummarySuccess', {
              updated: result.updated,
            }),
        result.failed > 0 ? 'warning' : 'success',
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedBulkTag');
      showToast(message, 'error');
    } finally {
      setIsBulkTagging(false);
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
      showToast(t('library.tagsUpdated'), 'success');

      if (activeTagFilter && !updatedCv.tags.includes(activeTagFilter)) {
        setActiveTagFilter('');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedSaveTags');
      showToast(message, 'error');
    } finally {
      setSavingTagCvId(null);
    }
  };

  const handleToggleFavorite = async (cvId: number) => {
    setTogglingFavoriteCvId(cvId);
    try {
      const updatedCv = await apiService.toggleFavoriteCV(cvId);
      setCvs((prev) => {
        const next = prev.map((cv) => (cv.id === cvId ? updatedCv : cv));
        return [...next].sort((a, b) => {
          if (a.is_favorite !== b.is_favorite) {
            return Number(b.is_favorite) - Number(a.is_favorite);
          }
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
      });
      setTagInputs((prev) => ({ ...prev, [cvId]: updatedCv.tags.join(', ') }));
      showToast(updatedCv.is_favorite ? t('library.favoriteAdded') : t('library.favoriteRemoved'), 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : t('library.failedFavoriteToggle');
      showToast(message, 'error');
    } finally {
      setTogglingFavoriteCvId(null);
    }
  };

  const availableTags = Array.from(new Set(cvs.flatMap((cv) => cv.tags))).sort((a, b) =>
    a.localeCompare(b),
  );
  const visibleCvs = cvs;
  const activeCv = visibleCvs.find((cv) => cv.id === selectedCvId) ?? visibleCvs[0] ?? null;
  const allVisibleSelected =
    visibleCvs.length > 0 && visibleCvs.every((cv) => selectedCvIds.includes(cv.id));

  return (
    <div className="space-y-4 animate-in fade-in duration-300 h-full">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4 dark:border-slate-800">
        <div>
          <h1 className="text-2xl lg:text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('library.title')}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">{t('library.subtitle')}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {selectedCvIds.length > 0 && (
            <>
              <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {t('library.selectedCount', { count: selectedCvIds.length })}
              </span>
              <input
                type="text"
                value={bulkTagInput}
                onChange={(e) => setBulkTagInput(e.target.value)}
                placeholder={t('library.bulkTagsPlaceholder')}
                className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none transition focus:border-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              />
              <button
                type="button"
                onClick={handleBulkTag}
                disabled={isBulkTagging || bulkTagInput.trim().length === 0}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-brand-primary/20 bg-brand-primary/10 px-4 text-xs font-semibold text-brand-primary transition-colors hover:bg-brand-primary/15 disabled:cursor-not-allowed disabled:opacity-60 dark:border-brand-secondary/20 dark:text-brand-secondary"
              >
                {isBulkTagging ? <Loader2 size={14} className="animate-spin" /> : <Tag size={14} />}
                {t('library.bulkApplyTags')}
              </button>
              <button
                type="button"
                onClick={() => setSelectedCvIds([])}
                className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {t('library.clearSelection')}
              </button>
              <button
                type="button"
                onClick={handleBulkDelete}
                disabled={isBulkDeleting}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 text-xs font-semibold text-rose-700 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300"
              >
                {isBulkDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                {t('library.bulkDelete')}
              </button>
            </>
          )}
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
                className={`relative overflow-hidden flex items-center justify-between p-2 rounded-lg border ${
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
                {item.status === 'uploading' && (
                  <div className="absolute bottom-0 left-0 h-[2px] bg-brand-primary animate-pulse w-full" />
                )}
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

      <div className="grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)] gap-4 min-h-[560px]">
        <aside className="glass-card p-3 rounded-2xl flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Tag size={14} />
              <span>{t('library.filterByTag')}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{visibleCvs.length}</span>
              {!isLoading && visibleCvs.length > 0 && (
                <button
                  type="button"
                  onClick={handleSelectAllVisible}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  {allVisibleSelected ? t('library.clearSelection') : t('library.selectAllVisible')}
                </button>
              )}
            </div>
          </div>

          <label className="relative mb-3 block">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t('library.searchPlaceholder')}
              className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-700 outline-none transition focus:border-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            />
          </label>

          <div className="flex flex-wrap gap-1.5 mb-3">
            <button
              onClick={() => {
                setActiveTagFilter('');
                setPagination((current) => ({ ...current, offset: 0 }));
              }}
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
                onClick={() => {
                  setActiveTagFilter(tag);
                  setPagination((current) => ({ ...current, offset: 0 }));
                }}
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
              <div className="space-y-3 py-1">
                <div className="skeleton-block h-8 w-24 rounded-full" />
                <SkeletonLoader lines={5} />
              </div>
            ) : visibleCvs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center h-full min-h-[200px]">
                {pagination.total === 0 && !searchQuery && !activeTagFilter ? (
                  <>
                    <div className="h-12 w-12 rounded-full bg-brand-primary/10 flex items-center justify-center mb-3">
                      <UploadCloud size={20} className="text-brand-primary" />
                    </div>
                    <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{t('library.noCvsYet')}</h3>
                    <p className="text-xs text-slate-500 mb-4 max-w-[180px]">{t('library.emptyLibrary')}</p>
                    <button onClick={handleUploadClick} className="btn-primary !py-1.5 px-4 text-xs">
                      {t('library.uploadFirstCv')}
                    </button>
                  </>
                ) : (
                  <>
                    <FileText size={24} className="text-slate-400 mb-2" />
                    <p className="text-xs text-slate-500">{t('library.noTagMatches')}</p>
                  </>
                )}
              </div>
            ) : (
              visibleCvs.map((cv) => (
                <div
                  key={cv.id}
                  className={`w-full text-left rounded-xl px-3 py-2 border transition-colors ${
                    activeCv?.id === cv.id
                      ? 'border-brand-primary bg-brand-primary/10'
                      : 'border-slate-200 bg-white/70 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/30 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={selectedCvIds.includes(cv.id)}
                      onChange={() => toggleCvSelection(cv.id)}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-primary focus:ring-brand-primary dark:border-slate-700 dark:bg-slate-900"
                      aria-label={`Select ${cv.name}`}
                    />
                    <button
                      type="button"
                      onClick={() => setSelectedCvId(cv.id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 break-words">{cv.name}</p>
                        {cv.is_favorite && (
                          <span className="inline-flex shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                            {t('library.favoriteBadge')}
                          </span>
                        )}
                      </div>
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
                    <button
                      type="button"
                      onClick={() => handleToggleFavorite(cv.id)}
                      disabled={togglingFavoriteCvId === cv.id}
                      className={`mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                        cv.is_favorite
                          ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300'
                          : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                      }`}
                      aria-label={cv.is_favorite ? t('library.unfavoriteAction') : t('library.favoriteAction')}
                      title={cv.is_favorite ? t('library.unfavoriteAction') : t('library.favoriteAction')}
                    >
                      {togglingFavoriteCvId === cv.id ? <Loader2 size={14} className="animate-spin" /> : <Star size={14} className={cv.is_favorite ? 'fill-current' : ''} />}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {!isLoading && pagination.total > 0 && (
            <PaginationControls
              className="mt-3"
              pagination={pagination}
              itemLabel={t('library.resultsLabel')}
              onPrevious={() =>
                setPagination((current) => ({
                  ...current,
                  offset: Math.max(0, current.offset - PAGE_SIZE),
                }))
              }
              onNext={() =>
                setPagination((current) => ({
                  ...current,
                  offset: current.offset + PAGE_SIZE,
                }))
              }
            />
          )}
        </aside>

        <section className="glass-card p-4 rounded-2xl min-h-0">
          {isLoading ? (
            <div className="space-y-4">
              <div className="skeleton-block h-8 w-1/3 rounded-xl" />
              <div className="skeleton-block h-4 w-1/4 rounded-xl" />
              <div className="rounded-xl border border-slate-200/70 p-4 dark:border-slate-800">
                <SkeletonLoader lines={6} />
              </div>
            </div>
          ) : !activeCv ? (
            <div className="h-full flex items-center justify-center text-center border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl bg-slate-50/50 dark:bg-slate-900/20">
              <div className="max-w-xs px-4">
                <div className="w-16 h-16 rounded-2xl bg-white dark:bg-slate-900 shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-center mx-auto mb-4">
                  <FileText size={28} className="text-brand-primary" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800 dark:text-gray-100 mb-2">{t('library.selectCvViewTitle')}</h3>
                <p className="text-sm text-slate-500 mb-5">{t('library.selectCvViewDesc')}</p>
                <button onClick={handleUploadClick} className="btn-primary mx-auto flex items-center justify-center gap-2 px-5 h-10 text-sm">
                  <UploadCloud size={16} />
                  {t('library.uploadNewCv')}
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col gap-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-heading font-bold text-brand-text dark:text-white">{activeCv.name}</h2>
                    {activeCv.is_favorite && (
                      <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                        {t('library.favoriteBadge')}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1"><Calendar size={12} /> {new Date(activeCv.created_at).toLocaleDateString(language)}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleToggleFavorite(activeCv.id)}
                    disabled={togglingFavoriteCvId === activeCv.id}
                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                      activeCv.is_favorite
                        ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                    }`}
                  >
                    {togglingFavoriteCvId === activeCv.id ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Star size={14} className={activeCv.is_favorite ? 'fill-current' : ''} />
                    )}
                    {activeCv.is_favorite ? t('library.unfavoriteAction') : t('library.favoriteAction')}
                  </button>
                  <button
                    onClick={() => handleDelete(activeCv.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-300"
                  >
                    <Trash2 size={14} />
                    {t('common.delete')}
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('library.summary')}</h3>
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
