import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RegisterPage } from './RegisterPage';

const registerMock = vi.fn();
const showToastMock = vi.fn();
const translateMock = vi.fn((key: string) => {
  const dictionary: Record<string, string> = {
    'auth.emailAddress': 'Email Address',
    'auth.password': 'Password',
    'auth.checkYourEmail': 'Check your email',
    'auth.confirmationEmailSent': "We've sent a confirmation link to ",
    'auth.clickToVerify': 'Click the link to verify your account and sign in.',
    'auth.backToLogin': 'Back to Sign In',
    'auth.emailHelper': 'Use the same email you want to use to sign in later.',
    'auth.passwordCaseSensitive': 'Passwords are case-sensitive.',
    'auth.passwordRequirementsTitle': 'Password requirements',
    'auth.passwordRequirementMinLength': 'At least 8 characters',
    'auth.passwordRequirementUppercase': 'At least one uppercase letter',
    'auth.passwordRequirementLowercase': 'At least one lowercase letter',
    'auth.passwordRequirementNumber': 'At least one number',
    'auth.createAccount': 'Create Account',
    'auth.creatingAccount': 'Creating account...',
    'auth.alreadyHaveAccount': 'Already have an account?',
    'auth.signIn': 'Sign In',
    'auth.accountCreated': 'Account created. Please sign in.',
    'auth.emailAlreadyExists': 'An account with this email already exists.',
    'auth.registrationFailed': 'Registration failed.',
  };

  return dictionary[key] ?? key;
});

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    register: registerMock,
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

describe('RegisterPage', () => {
  beforeEach(() => {
    registerMock.mockReset();
    showToastMock.mockReset();
    translateMock.mockClear();
  });

  it('shows the translated verification screen after successful registration', async () => {
    registerMock.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Email Address'), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'ValidPass123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create Account' }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith('user@example.com', 'ValidPass123');
      expect(showToastMock).toHaveBeenCalledWith('Account created. Please sign in.', 'success');
    });

    expect(await screen.findByText('Check your email')).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => {
        const text = element?.textContent ?? '';
        return (
          element?.tagName.toLowerCase() === 'p' &&
          text.includes("We've sent a confirmation link to") &&
          text.includes('user@example.com') &&
          text.includes('Click the link to verify your account and sign in.')
        );
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to Sign In' })).toBeInTheDocument();
  });
});