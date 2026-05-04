import React from 'react';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  children?: React.ReactNode;
};

export const Button: React.FC<ButtonProps> = ({ children, className = '', ...rest }) => {
  return (
    <button className={className} {...rest}>
      {children}
    </button>
  );
};

export default Button;
