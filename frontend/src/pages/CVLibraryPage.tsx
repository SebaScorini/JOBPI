import React, { useEffect, useState, useRef } from 'react';
import { apiService } from '../services/api';
import { StoredCV } from '../types';
import { FileText, Loader2, UploadCloud, Trash2, Calendar, CheckCircle, AlertCircle, X, Tag } from 'lucide-react';

interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function CVLibraryPage() {
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<UploadFile[]>([]);
  const [uploadResults, setUploadResults] = useState<Array<{ filename: string; success: boolean; error?: string }>>([]);
  const [tagInputs, setTagInputs] = useState<Record<number, string>>({});
  const [savingTagCvId, setSavingTagCvId] = useState<number | null>(null);
  const [activeTagFilter, setActiveTagFilter] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadCVs();
  }, []);

  const loadCVs = async () => {
    try {
      const data = await apiService.listCVs();
      setCvs(data);
      setTagInputs(
        data.reduce((acc, cv) => {
          acc[cv.id] = cv.tags.join(', ');
          return acc;
        }, {} as Record<number, string>)
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

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    // Add files to selected list
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
    setUploadResults([]);

    // Update all files to uploading
    setSelectedFiles((prev) =>
      prev.map((f) => ({ ...f, status: 'uploading' as const }))
    );

    try {
      const filesToUpload = selectedFiles.map((f) => f.file);
      const result = await apiService.batchUploadCVs(filesToUpload);

      // Update selected files with results
      const resultsMap = result.results.reduce(
        (acc, r) => {
          acc[r.filename] = r;
          return acc;
        },
        {} as Record<string, any>
      );

      setSelectedFiles((prev) =>
        prev.map((f) => {
          const uploadResult = resultsMap[f.file.name];
          return {
            ...f,
            status: uploadResult?.success ? ('success' as const) : ('error' as const),
            error: uploadResult?.error,
          };
        })
      );

      setUploadResults(result.results);

      // Reload CVs to show newly uploaded ones
      await loadCVs();

      // Clear successful uploads after a delay, keep failed ones visible
      setTimeout(() => {
        setSelectedFiles((prev) =>
          prev.filter((f) => f.status === 'error')
        );
      }, 2000);
    } catch (err) {
      console.error('Failed to upload CVs', err);
      setSelectedFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'error' as const,
          error: 'Upload failed',
        }))
      );
    } finally {
      setIsUploading(false);
    }
  };

  const clearUploadState = () => {
    setSelectedFiles([]);
    setUploadResults([]);
  };

  const successCount = selectedFiles.filter((f) => f.status === 'success').length;
  const errorCount = selectedFiles.filter((f) => f.status === 'error').length;

  const handleDelete = async (cvId: number) => {
    if (!window.confirm('Are you sure you want to delete this CV?')) return;
    
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

  const availableTags = Array.from(
    new Set(cvs.flatMap((cv) => cv.tags))
  ).sort((a, b) => a.localeCompare(b));

  const visibleCvs = activeTagFilter
    ? cvs.filter((cv) => cv.tags.includes(activeTagFilter))
    : cvs;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            CV Library
          </h1>
          <p className="text-slate-500 mt-2">Manage your uploaded resumes for automatic matching.</p>
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
             className="btn-primary flex items-center justify-center gap-2 w-auto px-6 h-12"
          >
            {isUploading ? <Loader2 size={18} className="animate-spin" /> : <UploadCloud size={18} />}
            Upload Resumes
          </button>
        </div>
      </div>

      {/* Selected Files Display */}
      {selectedFiles.length > 0 && (
        <div className="glass-card-solid p-6 rounded-3xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">
              Selected Files ({selectedFiles.length})
            </h2>
            {!isUploading && (
              <button
                onClick={clearUploadState}
                className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                Clear
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {selectedFiles.map((item, index) => (
              <div
                key={`${item.file.name}-${index}`}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                  item.status === 'success'
                    ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30'
                    : item.status === 'error'
                    ? 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/30'
                    : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText size={18} className="flex-shrink-0" />
                  <span className="text-sm font-medium truncate">{item.file.name}</span>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {item.status === 'uploading' && (
                    <Loader2 size={18} className="animate-spin text-brand-primary" />
                  )}
                  {item.status === 'success' && (
                    <CheckCircle size={18} className="text-emerald-500" />
                  )}
                  {item.status === 'error' && (
                    <AlertCircle size={18} className="text-rose-500" />
                  )}
                  {item.status === 'pending' && !isUploading && (
                    <button
                      onClick={() => removeSelectedFile(index)}
                      className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                    >
                      <X size={18} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error Messages */}
          {selectedFiles.some((f) => f.error) && (
            <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
              {selectedFiles
                .filter((f) => f.error)
                .map((item, index) => (
                  <div key={`error-${index}`} className="text-sm text-rose-600 dark:text-rose-400">
                    <span className="font-medium">{item.file.name}:</span> {item.error}
                  </div>
                ))}
            </div>
          )}

          {/* Upload Summary */}
          {(successCount > 0 || errorCount > 0) && (
            <div className="pt-2 border-t border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400">
              {successCount > 0 && (
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                  ✓ {successCount} uploaded successfully
                </span>
              )}
              {successCount > 0 && errorCount > 0 && <span> • </span>}
              {errorCount > 0 && (
                <span className="text-rose-600 dark:text-rose-400 font-medium">
                  ✗ {errorCount} failed
                </span>
              )}
            </div>
          )}

          {/* Upload Button */}
          {selectedFiles.some((f) => f.status === 'pending' || f.status === 'error') && !isUploading && (
            <button
              onClick={handleBatchUpload}
              disabled={isUploading}
              className="w-full btn-primary !bg-emerald-600 hover:!bg-emerald-500 py-2"
            >
              Upload {selectedFiles.filter((f) => f.status === 'pending').length} File(s)
            </button>
          )}
        </div>
      )}

      {availableTags.length > 0 && (
        <div className="glass-card-solid p-4 rounded-3xl space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-brand-text dark:text-white">
            <Tag size={16} />
            <span>Filter by tag</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTagFilter('')}
              className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
                activeTagFilter === ''
                  ? 'bg-brand-primary text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              All
            </button>
            {availableTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setActiveTagFilter(tag)}
                className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
                  activeTagFilter === tag
                    ? 'bg-brand-primary text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
        </div>
      ) : visibleCvs.length === 0 ? (
        <div className="text-center py-20 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-[#151B2B]/50">
          <FileText size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          {cvs.length === 0 ? (
            <>
              <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">Your library is empty</p>
              <p className="text-slate-500 max-w-sm mx-auto mb-6">Upload one or more resumes in PDF format to build your candidate pool.</p>
              <button onClick={handleUploadClick} className="btn-secondary w-auto px-8 mx-auto inline-flex items-center justify-center">
                Upload PDF
              </button>
            </>
          ) : (
            <>
              <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">No CVs match that tag</p>
              <p className="text-slate-500 max-w-sm mx-auto mb-6">Clear the filter or update tags on a CV to see it here.</p>
              <button onClick={() => setActiveTagFilter('')} className="btn-secondary w-auto px-8 mx-auto inline-flex items-center justify-center">
                Clear filter
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleCvs.map((cv) => (
            <div 
              key={cv.id} 
              className="glass-card-solid p-6 rounded-[1.5rem] flex flex-col justify-between group h-full relative"
            >
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={() => handleDelete(cv.id)}
                  className="p-2 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer"
                  title="Delete CV"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <div>
                <div className="w-12 h-12 rounded-[14px] bg-brand-primary/10 flex items-center justify-center text-brand-primary mb-5">
                  <FileText size={24} />
                </div>
                <h3 className="font-heading font-bold text-lg text-brand-text dark:text-white mb-2 break-words items-center pr-8">
                  {cv.name}
                </h3>
                <p className="text-sm text-slate-500 mb-4 line-clamp-3">{cv.summary}</p>
                <div className="flex flex-wrap gap-2 mb-4">
                  {cv.tags.length > 0 ? (
                    cv.tags.map((tag) => (
                      <button
                        key={tag}
                        onClick={() => setActiveTagFilter(tag)}
                        className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                      >
                        {tag}
                      </button>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400">No tags yet</span>
                  )}
                </div>
                <div className="space-y-2 mb-4">
                  <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Tags
                  </label>
                  <input
                    type="text"
                    value={tagInputs[cv.id] ?? ''}
                    onChange={(e) =>
                      setTagInputs((prev) => ({ ...prev, [cv.id]: e.target.value }))
                    }
                    placeholder="frontend, react, english"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                  />
                  <button
                    onClick={() => handleSaveTags(cv.id)}
                    disabled={savingTagCvId === cv.id}
                    className="btn-secondary w-full py-2 disabled:opacity-60"
                  >
                    {savingTagCvId === cv.id ? 'Saving...' : 'Save tags'}
                  </button>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-500 mt-auto">
                   <Calendar size={14} />
                   <span>{new Date(cv.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
