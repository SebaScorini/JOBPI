import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LoginPage } from './LoginPage';


const navigateMock = vi.fn();
const loginMock = vi.fn();
const showToastMock = vi.fn();
const loginApiMock = vi.fn();
const getMeMock = vi.fn();
const translateMock = vi.fn((key: string) => {
  const dictionary: Record<string, string> = {
    'auth.emailAddress': 'Email Address',
    'auth.password': 'Password',
    'auth.signIn': 'Sign In',
    'auth.signingIn': 'Signing in...',
    'auth.noAccount': "Don't have an account?",
    'auth.createOneNow': 'Create one now',
    'auth.emailHelper': 'Use the same email you want to use to sign in later.',
    'auth.passwordCaseSensitive': 'Passwords are case-sensitive.',
    'auth.loginSuccess': 'Signed in successfully.',
    'auth.loginFailed': 'Login failed.',
  };

  return dictionary[key] ?? key;
});

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}));

vi.mock('../context/LanguageContext', () => ({
  useLanguage: () => ({
    t: translateMock,
  }),
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({
    showToast: showToastMock,
  }),
}));

vi.mock('../services/api', () => ({
  ApiError: class ApiError extends Error {},
  apiService: {
    login: (...args: unknown[]) => loginApiMock(...args),
    getMe: (...args: unknown[]) => getMeMock(...args),
  },
}));


describe('LoginPage', () => {
  beforeEach(() => {
    navigateMock.mockReset();
    loginMock.mockReset();
    showToastMock.mockReset();
    loginApiMock.mockReset();
    getMeMock.mockReset();
    translateMock.mockClear();
  });

  it('shows validation errors for an invalid email and missing password', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Email Address'), { target: { value: 'invalid-email' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Sign In' }).closest('form')!);

    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Password is required.')).toBeInTheDocument();
    expect(loginApiMock).not.toHaveBeenCalled();
  });

  it('submits valid credentials and redirects to the dashboard', async () => {
    loginApiMock.mockResolvedValue({ access_token: 'token-123' });
    getMeMock.mockResolvedValue({ id: 1, email: 'user@example.com', is_active: true, created_at: '2026-01-01' });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Email Address'), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'ValidPass123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign In' }));

    await waitFor(() => {
      expect(loginApiMock).toHaveBeenCalledWith('user@example.com', 'ValidPass123');
      expect(getMeMock).toHaveBeenCalledWith('token-123');
      expect(loginMock).toHaveBeenCalled();
      expect(showToastMock).toHaveBeenCalledWith('Signed in successfully.', 'success');
      expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });
});
