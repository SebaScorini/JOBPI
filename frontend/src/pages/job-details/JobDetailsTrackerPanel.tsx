import type { JobApplicationStatus } from '../../types';

interface StatusOption {
  value: JobApplicationStatus;
  label: string;
}

interface JobDetailsTrackerPanelProps {
  status: JobApplicationStatus;
  statusOptions: StatusOption[];
  handleStatusChange: (status: JobApplicationStatus) => void;
  isUpdatingStatus: boolean;
  notesDraft: string;
  setNotesDraft: (value: string) => void;
  handleSaveNotes: () => void;
  isSavingNotes: boolean;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export function JobDetailsTrackerPanel({
  status,
  statusOptions,
  handleStatusChange,
  isUpdatingStatus,
  notesDraft,
  setNotesDraft,
  handleSaveNotes,
  isSavingNotes,
  t,
}: JobDetailsTrackerPanelProps) {
  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <label className="mb-2 block text-xs font-semibold uppercase text-slate-500">{t('jobDetails.status')}</label>
        <select
          value={status}
          onChange={(e) => handleStatusChange(e.target.value as JobApplicationStatus)}
          disabled={isUpdatingStatus}
          className="input-field"
        >
          {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </div>

      <div>
        <label className="mb-2 block text-xs font-semibold uppercase text-slate-500">{t('jobDetails.notes')}</label>
        <textarea
          value={notesDraft}
          onChange={(e) => setNotesDraft(e.target.value)}
          rows={7}
          placeholder={t('jobDetails.notesPlaceholder')}
          className="input-field resize-y"
        />
      </div>

      <button onClick={handleSaveNotes} disabled={isSavingNotes} className="btn-secondary w-full px-6 sm:w-auto">
        {isSavingNotes ? t('jobDetails.savingNotes') : t('jobDetails.saveNotes')}
      </button>
    </div>
  );
}
