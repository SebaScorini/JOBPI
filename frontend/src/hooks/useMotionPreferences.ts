import { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

const MOBILE_BREAKPOINT = 768;

function readIsMobile() {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.innerWidth < MOBILE_BREAKPOINT;
}

export function useMotionPreferences() {
  const prefersReducedMotion = useReducedMotion();
  const [isMobile, setIsMobile] = useState(readIsMobile);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const update = (event?: MediaQueryListEvent) => {
      setIsMobile(event ? event.matches : mediaQuery.matches);
    };

    update();

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', update);
      return () => mediaQuery.removeEventListener('change', update);
    }

    mediaQuery.addListener(update);
    return () => mediaQuery.removeListener(update);
  }, []);

  return {
    isMobile,
    prefersReducedMotion,
    allowRichMotion: !isMobile && !prefersReducedMotion,
  };
}
