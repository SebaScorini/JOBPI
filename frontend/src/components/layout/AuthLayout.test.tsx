import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthLayout } from './AuthLayout';

const navigateMock = vi.fn();
const useAuthMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('../../context/LanguageContext', () => ({
  useLanguage: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('../../context/AppThemeContext', () => ({
  useAppTheme: () => ({
    resolvedTheme: 'light',
    toggleDarkMode: vi.fn(),
  }),
}));

vi.mock('../LanguageSelector', () => ({
  LanguageSelector: () => null,
}));

describe('AuthLayout', () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useAuthMock.mockReset();
  });

  it('redirects authenticated users from login to the dashboard', async () => {
    useAuthMock.mockReturnValue({
      user: { id: 'user-1' },
      isLoading: false,
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthLayout />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('keeps authenticated users on the reset password route', async () => {
    useAuthMock.mockReturnValue({
      user: { id: 'user-1' },
      isLoading: false,
    });

    render(
      <MemoryRouter initialEntries={['/reset-password']}>
        <AuthLayout />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(navigateMock).not.toHaveBeenCalled();
    });
  });
});
