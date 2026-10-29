import React from 'react';
import { cn } from '../../lib/utils';

export const LoadingSkeleton: React.FC<{ count?: number; className?: string }> = ({
  count = 3,
  className,
}) => {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'h-14 rounded-lg bg-muted/60 animate-pulse border border-border/40',
            className
          )}
        />
      ))}
    </div>
  );
};
