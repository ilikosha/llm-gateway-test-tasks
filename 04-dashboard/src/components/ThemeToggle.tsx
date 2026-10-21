import type { Theme } from '../lib/theme';

interface Props {
  theme: Theme;
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: Props) {
  const next = theme === 'dark' ? 'светлую' : 'тёмную';
  return (
    <button
      type="button"
      className="btn btn-secondary shrink-0"
      onClick={onToggle}
      aria-label={`Переключить на ${next} тему`}
      title={`Переключить на ${next} тему`}
    >
      <span aria-hidden="true">{theme === 'dark' ? '☀️' : '🌙'}</span>
    </button>
  );
}
