import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { LogIn, Loader2 } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const tokenData = await apiService.login(email, password);
      const user = await apiService.getMe(tokenData.access_token);
      login(tokenData.access_token, user);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Login failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in duration-300">
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-sm font-medium">
          {error}
        </div>
      )}
      
      <div>
        <label className="block text-sm font-semibold mb-2">Email Address</label>
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
        <label className="block text-sm font-semibold mb-2">Password</label>
        <input 
          type="password" 
          required 
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="input-field" 
          placeholder="••••••••"
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary flex items-center justify-center gap-2 mt-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <LogIn size={18} />}
        Sign In
      </button>
      
      <p className="text-center text-sm font-medium text-slate-500 mt-6">
        Don't have an account?{' '}
        <Link to="/register" className="text-brand-primary hover:underline">
          Create one now
        </Link>
      </p>
    </form>
  );
}
