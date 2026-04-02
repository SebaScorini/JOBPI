import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { UserPlus, Loader2 } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { t } = useLanguage();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await apiService.register(email, password);
      // Directly login after registration
      navigate('/login');
    } catch (err: any) {
      setError(err.message || t('auth.registrationFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in zoom-in-95 duration-300">
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-sm font-medium">
          {error}
        </div>
      )}
      
      <div>
        <label className="block text-sm font-semibold mb-2">{t('auth.emailAddress')}</label>
        <input 
          type="email" 
          required 
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="input-field" 
          placeholder="user@example.com"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-2">{t('auth.password')}</label>
        <input 
          type="password" 
          required 
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="input-field" 
          placeholder="••••••••"
          minLength={6}
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary flex items-center justify-center gap-2 mt-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <UserPlus size={18} />}
        {t('auth.createAccount')}
      </button>
      
      <p className="text-center text-sm font-medium text-slate-500 mt-6">
        {t('auth.alreadyHaveAccount')}{' '}
        <Link to="/login" className="text-brand-primary hover:underline">
          {t('auth.signIn')}
        </Link>
      </p>
    </form>
  );
}
