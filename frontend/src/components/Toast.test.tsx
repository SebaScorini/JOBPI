import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ToastViewport } from './Toast';
import { ToastProvider, useToast } from '../context/ToastContext';


function ToastHarness() {
  const { showToast } = useToast();

  return (
    <div>
      <button type="button" onClick={() => showToast('Saved successfully.', 'success', 5000)}>
        Show success
      </button>
      <ToastViewport />
    </div>
  );
}


describe('ToastViewport', () => {
  it('renders and dismisses a toast notification', () => {
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show success' }));

    expect(screen.getByText('Saved successfully.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }));
    expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument();
  });

  it('auto-dismisses toasts after their duration', () => {
    vi.useFakeTimers();

    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Show success' }));
    expect(screen.getByText('Saved successfully.')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument();
    vi.useRealTimers();
  });
});
