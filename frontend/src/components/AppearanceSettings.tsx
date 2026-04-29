import React, { useState, useRef, useEffect } from 'react';
import { useAppearance } from '../hooks/useAppearance';
import { Type, Check, TypeOutline, Monitor, Expand, Shrink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const FONT_SIZES = [
  { id: '85%', label: 'Compacto', icon: Shrink, description: 'Más contenido en pantalla' },
  { id: '90%', label: 'Estándar', icon: Monitor, description: 'Equilibrio perfecto' },
  { id: '100%', label: 'Cómodo', icon: Expand, description: 'Lectura relajada' },
  { id: '110%', label: 'Grande', icon: Type, description: 'Máxima legibilidad' },
] as const;

const FONT_FAMILIES = [
  { id: 'DM Sans', label: 'DM Sans', description: 'Por defecto' },
  { id: 'Inter', label: 'Inter', description: 'Limpia y neutral' },
  { id: 'Outfit', label: 'Outfit', description: 'Moderna y geométrica' },
  { id: 'Plus Jakarta Sans', label: 'Plus Jakarta', description: 'Premium y legible' },
] as const;

export function AppearanceSettings() {
  const { fontSize, setFontSize, fontFamily, setFontFamily } = useAppearance();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2.5 rounded-xl transition-colors flex items-center gap-2 ${
          isOpen 
            ? 'bg-brand-primary/10 text-brand-primary dark:bg-brand-secondary/10 dark:text-brand-secondary' 
            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-brand-primary dark:hover:text-brand-secondary hover:bg-slate-200 dark:hover:bg-slate-700'
        }`}
        aria-label="Ajustes de apariencia"
        title="Apariencia"
      >
        <Type size={18} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute right-0 mt-2 w-72 glass-card-solid rounded-2xl shadow-xl border border-slate-200/60 dark:border-slate-700/50 overflow-hidden z-50 origin-top-right"
          >
            <div className="p-4 border-b border-slate-100 dark:border-slate-800/80">
              <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm mb-1">
                Apariencia Visual
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Personaliza la lectura a tu gusto
              </p>
            </div>

            <div className="p-3 max-h-[60vh] overflow-y-auto">
              <div className="mb-4">
                <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2 px-1">
                  Tamaño de texto
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {FONT_SIZES.map((size) => {
                    const isSelected = fontSize === size.id;
                    const Icon = size.icon;
                    return (
                      <button
                        key={size.id}
                        onClick={() => setFontSize(size.id as any)}
                        className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all ${
                          isSelected
                            ? 'border-brand-primary bg-brand-primary/5 text-brand-primary dark:border-brand-secondary dark:bg-brand-secondary/10 dark:text-brand-secondary shadow-sm'
                            : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                        }`}
                      >
                        <Icon size={18} className="mb-1.5 opacity-80" />
                        <span className="text-xs font-semibold">{size.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2 px-1">
                  Tipografía
                </p>
                <div className="space-y-1">
                  {FONT_FAMILIES.map((font) => {
                    const isSelected = fontFamily === font.id;
                    return (
                      <button
                        key={font.id}
                        onClick={() => setFontFamily(font.id as any)}
                        style={{ fontFamily: `"${font.id}", sans-serif` }}
                        className={`w-full flex items-center justify-between p-3 rounded-xl transition-all ${
                          isSelected
                            ? 'bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/10 dark:text-brand-secondary'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/80'
                        }`}
                      >
                        <div className="flex flex-col items-start">
                          <span className="text-sm font-medium">{font.label}</span>
                          <span className="text-[10px] opacity-70 mt-0.5">{font.description}</span>
                        </div>
                        {isSelected && <Check size={16} />}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
