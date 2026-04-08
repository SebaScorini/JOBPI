import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { UserPlus, Loader2 } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { registerSchema } from '../utils/validation';
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
      showToast('Account created. Please sign in.', 'success');
      navigate('/login');
    } catch (err: any) {
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
        <label className="mb-2 block text-sm font-semibold">{t('auth.emailAddress')}</label>
        <input
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (fieldErrors.email) {
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }
          }}
          className={`input-field ${fieldErrors.email ? 'input-field-error' : ''}`}
          placeholder="user@example.com"
          aria-invalid={Boolean(fieldErrors.email)}
        />
        {fieldErrors.email && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.email}</p>}
      </div>

      <div>
        <label className="mb-2 block text-sm font-semibold">{t('auth.password')}</label>
        <input
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (fieldErrors.password) {
              setFieldErrors((current) => ({ ...current, password: undefined }));
            }
          }}
          className={`input-field ${fieldErrors.password ? 'input-field-error' : ''}`}
          placeholder="Create a password"
          aria-invalid={Boolean(fieldErrors.password)}
        />
        {fieldErrors.password && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.password}</p>}
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary mt-2 flex items-center justify-center gap-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <UserPlus size={18} />}
        {t('auth.createAccount')}
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
