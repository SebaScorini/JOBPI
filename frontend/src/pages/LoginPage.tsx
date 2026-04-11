import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ApiError, apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { LogIn, Loader2 } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { loginSchema } from '../utils/validation';
import { useToast } from '../context/ToastContext';

interface LoginFieldErrors {
  email?: string;
  password?: string;
}

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const { t } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const applyBackendFieldErrors = (apiError: ApiError) => {
    const nextErrors: LoginFieldErrors = {};

    if (apiError.status === 401) {
      nextErrors.email = t('auth.invalidCredentials');
      nextErrors.password = t('auth.invalidCredentials');
    }

    if (apiError.status === 403) {
      nextErrors.email = t('auth.inactiveAccount');
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

    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      const nextErrors: LoginFieldErrors = {};
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
      const tokenData = await apiService.login(parsed.data.email, parsed.data.password);
      const user = await apiService.getMe(tokenData.access_token);
      login(tokenData.access_token, user);
      showToast(t('auth.loginSuccess'), 'success');
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      if (err instanceof ApiError && applyBackendFieldErrors(err)) {
        setError(err.status === 401 ? t('auth.invalidCredentialsHint') : '');
        return;
      }

      const message = err.message || t('auth.loginFailed');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in duration-300">
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-600">
          {error}
        </div>
      )}

      <div>
        <label className="mb-2 block text-sm font-semibold">{t('auth.emailAddress')}</label>
        <input
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
          placeholder={t('auth.emailPlaceholder')}
          aria-invalid={Boolean(fieldErrors.email)}
        />
        {fieldErrors.email && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.email}</p>}
        {!fieldErrors.email && <p className="mt-2 text-xs text-slate-500">{t('auth.emailHelper')}</p>}
      </div>

      <div>
        <label className="mb-2 block text-sm font-semibold">{t('auth.password')}</label>
        <input
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
          placeholder={t('auth.passwordPlaceholder')}
          aria-invalid={Boolean(fieldErrors.password)}
        />
        {fieldErrors.password && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.password}</p>}
        {!fieldErrors.password && <p className="mt-2 text-xs text-slate-500">{t('auth.passwordCaseSensitive')}</p>}
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary mt-2 flex items-center justify-center gap-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <LogIn size={18} />}
        {isLoading ? t('auth.signingIn') : t('auth.signIn')}
      </button>

      <p className="mt-6 text-center text-sm font-medium text-slate-500">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className="text-brand-primary hover:underline">
          {t('auth.createOneNow')}
        </Link>
      </p>
    </form>
  );
}
