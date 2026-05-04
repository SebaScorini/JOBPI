import React from 'react';

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  children?: React.ReactNode;
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, className = '', ...rest }, ref) => {
    // Only add glass-card if className doesn't already contain a glass-card variant
    const hasGlassCardVariant = className.includes('glass-card');
    const finalClassName = hasGlassCardVariant ? className : `${className} glass-card`.trim();
    
    return (
      <div ref={ref} className={finalClassName} {...rest}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export default Card;
