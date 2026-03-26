import React, { useEffect, useState, useRef } from 'react';
import { apiService } from '../services/api';
import { StoredCV } from '../types';
import { FileText, Loader2, UploadCloud, Trash2, Calendar } from 'lucide-react';

export function CVLibraryPage() {
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadCVs();
  }, []);

  const loadCVs = async () => {
    try {
      const data = await apiService.listCVs();
      setCvs(data);
    } catch (err) {
      console.error('Failed to load CVs', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    setIsUploading(true);
    try {
      const newCv = await apiService.uploadCV(file.name, file);
      setCvs((prev) => [newCv, ...prev]);
    } catch (err) {
      console.error('Failed to upload CV', err);
      alert('Upload failed. Please ensure backend size limits and correct file type.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (cvId: number) => {
    if (!window.confirm('Are you sure you want to delete this CV?')) return;
    
    try {
      await apiService.deleteCV(cvId);
      setCvs((prev) => prev.filter((cv) => cv.id !== cvId));
    } catch (err) {
      console.error('Failed to delete CV', err);
    }
  };

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
             accept="application/pdf"
             className="hidden" 
          />
          <button 
             onClick={handleUploadClick} 
             disabled={isUploading}
             className="btn-primary flex items-center justify-center gap-2 w-auto px-6 h-12"
          >
            {isUploading ? <Loader2 size={18} className="animate-spin" /> : <UploadCloud size={18} />}
            Upload Resume
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
        </div>
      ) : cvs.length === 0 ? (
        <div className="text-center py-20 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-[#151B2B]/50">
          <FileText size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">Your library is empty</p>
          <p className="text-slate-500 max-w-sm mx-auto mb-6">Upload your first resume in PDF format to build your candidate pool.</p>
          <button onClick={handleUploadClick} className="btn-secondary w-auto px-8 mx-auto inline-flex items-center justify-center">
            Upload PDF
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cvs.map((cv) => (
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
