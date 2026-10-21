import type { Filters, RequestRecord, SortState } from '../types';

export const EMPTY_FILTERS: Filters = { model: '', status: null, from: '', to: '' };

const DAY_MS = 24 * 3600 * 1000;

/** Начало дня (UTC) для строки YYYY-MM-DD; NaN, если строка некорректна. */
const startOfDay = (date: string): number => Date.parse(`${date}T00:00:00.000Z`);

/** Применяет фильтры; пустое значение фильтра означает «не фильтровать». Диапазон дат включает обе границы (UTC). */
export function filterRecords(records: readonly RequestRecord[], filters: Filters): RequestRecord[] {
  const from = filters.from ? startOfDay(filters.from) : Number.NEGATIVE_INFINITY;
  const toExclusive = filters.to ? startOfDay(filters.to) + DAY_MS : Number.POSITIVE_INFINITY;

  return records.filter((record) => {
    if (filters.model && record.model !== filters.model) return false;
    if (filters.status !== null && record.status !== filters.status) return false;
    const time = Date.parse(record.time);
    return time >= from && time < toExclusive;
  });
}

/** Возвращает новый отсортированный массив; при равенстве ключей порядок стабилен по id. */
export function sortRecords(records: readonly RequestRecord[], { key, dir }: SortState): RequestRecord[] {
  const sign = dir === 'asc' ? 1 : -1;
  const value = (r: RequestRecord): number => (key === 'time' ? Date.parse(r.time) : r[key]);
  return [...records].sort((a, b) => sign * (value(a) - value(b)) || a.id - b.id);
}

export interface Page<T> {
  items: T[];
  page: number;
  pageCount: number;
}

/** Страница нумеруется с 1 и зажимается в допустимый диапазон. */
export function paginate<T>(items: readonly T[], page: number, pageSize: number): Page<T> {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const current = Math.min(Math.max(1, Math.trunc(page) || 1), pageCount);
  const start = (current - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), page: current, pageCount };
}

/** Уникальные значения моделей, по алфавиту. */
export function uniqueModels(records: readonly RequestRecord[]): string[] {
  return [...new Set(records.map((r) => r.model))].sort((a, b) => a.localeCompare(b));
}

/** true, если задан хотя бы один фильтр. */
export function hasActiveFilters(filters: Filters): boolean {
  return Boolean(filters.model || filters.status !== null || filters.from || filters.to);
}
