import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Loader2, CheckCircle2, Circle, MailCheck } from 'lucide-react';
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
  const [registrationComplete, setRegistrationComplete] = useState(false);

  const { register } = useAuth();
  const { t } = useLanguage();
  const { showToast } = useToast();
  const passwordRequirements = getPasswordRequirementState(password);
  const passwordRequirementItems = [
    { key: 'minLength', label: t('auth.passwordRequirementMinLength'), met: passwordRequirements.minLength },
    { key: 'uppercase', label: t('auth.passwordRequirementUppercase'), met: passwordRequirements.uppercase },
    { key: 'lowercase', label: t('auth.passwordRequirementLowercase'), met: passwordRequirements.lowercase },
    { key: 'digit', label: t('auth.passwordRequirementNumber'), met: passwordRequirements.digit },
  ];

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
      await register(parsed.data.email, parsed.data.password);
      setRegistrationComplete(true);
      showToast(t('auth.accountCreated'), 'success');
    } catch (err: any) {
      const message = err?.message || t('auth.registrationFailed');

      if (message.toLowerCase().includes('already registered') || message.toLowerCase().includes('already been registered')) {
        setFieldErrors({ email: t('auth.emailAlreadyExists') });
      } else {
        setError(message);
        showToast(message, 'error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Show confirmation screen after successful registration
  if (registrationComplete) {
    return (
      <div className="space-y-6 text-center animate-in fade-in zoom-in-95 duration-300">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950/60">
          <MailCheck size={32} className="text-emerald-600 dark:text-emerald-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {t('auth.checkYourEmail')}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('auth.confirmationEmailSent')}
          <strong className="text-slate-700 dark:text-slate-200">{email}</strong>.
          {' '}
          {t('auth.clickToVerify')}
        </p>
        <Link
          to="/login"
          className="btn-primary mt-4 inline-flex items-center justify-center gap-2"
        >
          {t('auth.backToLogin')}
        </Link>
      </div>
    );
  }

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
