import { describe, expect, it } from 'vitest';

import { isTheme, resolveTheme, toggleTheme } from './theme';

describe('resolveTheme', () => {
  it('использует сохранённое значение, даже если оно расходится с системной темой', () => {
    expect(resolveTheme('light', true)).toBe('light');
    expect(resolveTheme('dark', false)).toBe('dark');
  });
  it('без сохранённого значения следует prefers-color-scheme', () => {
    expect(resolveTheme(null, true)).toBe('dark');
    expect(resolveTheme(null, false)).toBe('light');
  });
  it('игнорирует мусор в хранилище', () => {
    expect(resolveTheme('blue', true)).toBe('dark');
  });
});

describe('toggleTheme / isTheme', () => {
  it('переключает тему', () => {
    expect(toggleTheme('light')).toBe('dark');
    expect(toggleTheme('dark')).toBe('light');
  });
  it('проверяет тип', () => {
    expect(isTheme('dark')).toBe(true);
    expect(isTheme('x')).toBe(false);
    expect(isTheme(null)).toBe(false);
  });
});
