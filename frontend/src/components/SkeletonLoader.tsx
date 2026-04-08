import React from 'react';

interface SkeletonLoaderProps {
  className?: string;
  lines?: number;
}

export function SkeletonLoader({ className = '', lines = 1 }: SkeletonLoaderProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`skeleton-block ${index === lines - 1 ? 'w-4/5' : 'w-full'} h-4 rounded-xl`}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`glass-card-solid rounded-2xl p-5 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="skeleton-block h-10 w-10 rounded-xl" />
        <div className="skeleton-block h-6 w-24 rounded-full" />
      </div>
      <SkeletonLoader lines={3} />
      <div className="mt-5 flex gap-2">
        <div className="skeleton-block h-7 w-20 rounded-full" />
        <div className="skeleton-block h-7 w-16 rounded-full" />
      </div>
    </div>
  );
}
