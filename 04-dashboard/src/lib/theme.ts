export type Theme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'theme';

export const isTheme = (value: unknown): value is Theme => value === 'light' || value === 'dark';

/** Сохранённый выбор приоритетнее системной настройки prefers-color-scheme. */
export function resolveTheme(stored: string | null, prefersDark: boolean): Theme {
  if (isTheme(stored)) return stored;
  return prefersDark ? 'dark' : 'light';
}

export const toggleTheme = (theme: Theme): Theme => (theme === 'dark' ? 'light' : 'dark');

export function readStoredTheme(): string | null {
  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage недоступен (приватный режим и т.п.): тема просто не запомнится
  }
}
