import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ErrorBoundary } from './ErrorBoundary';

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>healthy content</div>;
}

describe('ErrorBoundary', () => {
  // Suppress error output during boundary tests
  const originalConsoleError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>hello world</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText('hello world')).toBeDefined();
  });

  it('renders fallback when a child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeDefined();
    expect(screen.getByRole('alert')).toBeDefined();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>custom error</div>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('custom error')).toBeDefined();
  });

  it('calls onError callback when a child throws', () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect(onError.mock.calls[0][0].message).toBe('Test error');
  });

  it('resets when the Try Again button is clicked', async () => {
    const user = userEvent.setup();

    // We need a component that can toggle throwing behavior
    let shouldThrow = true;
    function ToggleChild() {
      if (shouldThrow) {
        throw new Error('Toggle error');
      }
      return <div>recovered</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ToggleChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeDefined();

    // Fix the child before clicking retry
    shouldThrow = false;
    const retryButton = screen.getByText('Try Again');
    await user.click(retryButton);

    // After reset, boundary should re-render children
    rerender(
      <ErrorBoundary>
        <ToggleChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('recovered')).toBeDefined();
  });

  it('auto-resets when resetKeys change', () => {
    let shouldThrow = true;
    function ConditionalChild() {
      if (shouldThrow) {
        throw new Error('Reset key error');
      }
      return <div>reset recovered</div>;
    }

    const { rerender } = render(
      <ErrorBoundary resetKeys={['/old-path']}>
        <ConditionalChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeDefined();

    // Fix child and change reset key (simulating navigation)
    shouldThrow = false;
    rerender(
      <ErrorBoundary resetKeys={['/new-path']}>
        <ConditionalChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('reset recovered')).toBeDefined();
  });
});
