import { useCallback, useEffect, useState } from 'react';

import { readStoredTheme, resolveTheme, storeTheme, toggleTheme } from './lib/theme';
import type { Theme } from './lib/theme';

const prefersDark = (): boolean => window.matchMedia('(prefers-color-scheme: dark)').matches;

/** Тема: сохранённый выбор, иначе системная; без явного выбора следует за изменением системной темы. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => resolveTheme(readStoredTheme(), prefersDark()));

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setTheme(resolveTheme(readStoredTheme(), media.matches));
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next = toggleTheme(prev);
      storeTheme(next);
      return next;
    });
  }, []);

  return [theme, toggle];
}
