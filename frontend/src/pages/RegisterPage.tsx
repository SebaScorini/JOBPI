import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ApiError, apiService } from '../services/api';
import { UserPlus, Loader2, CheckCircle2, Circle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { getPasswordRequirementState, registerSchema } from '../utils/validation';
import { useToast } from '../context/ToastContext';

interface RegisterFieldErrors {
  email?: string;
  password?: string;
}

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<RegisterFieldErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  const { t } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const passwordRequirements = getPasswordRequirementState(password);
  const passwordRequirementItems = [
    { key: 'minLength', label: t('auth.passwordRequirementMinLength'), met: passwordRequirements.minLength },
    { key: 'uppercase', label: t('auth.passwordRequirementUppercase'), met: passwordRequirements.uppercase },
    { key: 'lowercase', label: t('auth.passwordRequirementLowercase'), met: passwordRequirements.lowercase },
    { key: 'digit', label: t('auth.passwordRequirementNumber'), met: passwordRequirements.digit },
  ];

  const applyBackendFieldErrors = (apiError: ApiError) => {
    const nextErrors: RegisterFieldErrors = {};

    if (apiError.status === 409 && apiError.message.toLowerCase().includes('email')) {
      nextErrors.email = t('auth.emailAlreadyExists');
    }

    for (const detail of apiError.details ?? []) {
      const fieldName = detail.loc?.[detail.loc.length - 1];
      if ((fieldName === 'email' || fieldName === 'password') && detail.msg) {
        nextErrors[fieldName] = detail.msg;
      }
    }

    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors);
      return true;
    }

    return false;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const parsed = registerSchema.safeParse({ email, password });
    if (!parsed.success) {
      const nextErrors: RegisterFieldErrors = {};
      for (const issue of parsed.error.issues) {
        const fieldName = issue.path[0];
        if (fieldName === 'email' || fieldName === 'password') {
          nextErrors[fieldName] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    setIsLoading(true);

    try {
      await apiService.register(parsed.data.email, parsed.data.password);
      showToast(t('auth.accountCreated'), 'success');
      navigate('/login');
    } catch (err: any) {
      if (err instanceof ApiError && applyBackendFieldErrors(err)) {
        setError('');
        return;
      }

      const message = err.message || t('auth.registrationFailed');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in zoom-in-95 duration-300">
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-600">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="register-email" className="mb-2 block text-sm font-semibold">
          {t('auth.emailAddress')}
        </label>
        <input
          id="register-email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (error) {
              setError('');
            }
            if (fieldErrors.email) {
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }
          }}
          className={`input-field ${fieldErrors.email ? 'input-field-error' : ''}`}
          placeholder="user@example.com"
          aria-invalid={Boolean(fieldErrors.email)}
        />
        {fieldErrors.email && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.email}</p>}
        {!fieldErrors.email && <p className="mt-2 text-xs text-slate-500">{t('auth.emailHelper')}</p>}
      </div>

      <div>
        <label htmlFor="register-password" className="mb-2 block text-sm font-semibold">
          {t('auth.password')}
        </label>
        <input
          id="register-password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (error) {
              setError('');
            }
            if (fieldErrors.password) {
              setFieldErrors((current) => ({ ...current, password: undefined }));
            }
          }}
          className={`input-field ${fieldErrors.password ? 'input-field-error' : ''}`}
          placeholder="Create a password"
          aria-invalid={Boolean(fieldErrors.password)}
        />
        {fieldErrors.password && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.password}</p>}
        {!fieldErrors.password && <p className="mt-2 text-xs text-slate-500">{t('auth.passwordCaseSensitive')}</p>}

        <div className="mt-3 rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:to-slate-950">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              {t('auth.passwordRequirementsTitle')}
            </p>
            <span className="rounded-full bg-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {passwordRequirementItems.filter((item) => item.met).length}/{passwordRequirementItems.length}
            </span>
          </div>

          <ul className="space-y-2">
            {passwordRequirementItems.map((item) => {
              const Icon = item.met ? CheckCircle2 : Circle;

              return (
                <li
                  key={item.key}
                  className={`flex items-center gap-3 rounded-xl border px-3 py-2 text-sm transition-all ${
                    item.met
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300'
                      : 'border-slate-200 bg-white text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400'
                  }`}
                >
                  <Icon size={16} className={item.met ? 'shrink-0' : 'shrink-0 opacity-70'} />
                  <span className={item.met ? 'font-medium' : ''}>{item.label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary mt-2 flex items-center justify-center gap-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <UserPlus size={18} />}
        {isLoading ? t('auth.creatingAccount') : t('auth.createAccount')}
      </button>

      <p className="mt-6 text-center text-sm font-medium text-slate-500">
        {t('auth.alreadyHaveAccount')}{' '}
        <Link to="/login" className="text-brand-primary hover:underline">
          {t('auth.signIn')}
        </Link>
      </p>
    </form>
  );
}
