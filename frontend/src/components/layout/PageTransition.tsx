import React, { ReactNode } from 'react';
import { motion, Transition } from 'framer-motion';
import { useLocation } from 'react-router-dom';

interface PageTransitionProps {
  children: ReactNode;
}

const pageVariants = {
  initial: {
    opacity: 0,
    y: 10,
    scale: 0.98,
  },
  in: {
    opacity: 1,
    y: 0,
    scale: 1,
  },
  out: {
    opacity: 0,
    y: -10,
    scale: 0.98,
  },
};

const pageTransition: Transition = {
  type: 'spring',
  stiffness: 300,
  damping: 30,
  mass: 1,
};

export const PageTransition: React.FC<PageTransitionProps> = ({ children }) => {
  const location = useLocation();
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  const activeVariants = isMobile ? {
    initial: { opacity: 0 },
    in: { opacity: 1 },
    out: { opacity: 0 }
  } : pageVariants;

  const activeTransition: Transition = isMobile ? {
    duration: 0.2, ease: "easeOut"
  } : pageTransition;

  return (
    <motion.div
      key={location.pathname}
      initial="initial"
      animate="in"
      exit="out"
      variants={activeVariants}
      transition={activeTransition}
      className="w-full h-full"
    >
      {children}
    </motion.div>
  );
};
