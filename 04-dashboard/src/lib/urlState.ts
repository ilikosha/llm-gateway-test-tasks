import { STATUS_CODES } from '../types';
import type { Filters, SortKey, SortState, StatusCode } from '../types';
import { EMPTY_FILTERS } from './filters';

export interface ViewState {
  filters: Filters;
  sort: SortState;
  page: number;
}

export const DEFAULT_SORT: SortState = { key: 'time', dir: 'desc' };
export const DEFAULT_VIEW: ViewState = { filters: EMPTY_FILTERS, sort: DEFAULT_SORT, page: 1 };

const SORT_KEYS: readonly SortKey[] = ['time', 'latencyMs', 'costUsd'];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

const parseDate = (value: string | null): string =>
  value && DATE_RE.test(value) && !Number.isNaN(Date.parse(value)) ? value : '';

function parseStatus(value: string | null): StatusCode | null {
  const code = Number(value);
  return STATUS_CODES.find((s) => s === code) ?? null;
}

/** Разбор query-строки; некорректные значения молча заменяются значениями по умолчанию. */
export function parseViewState(search: string): ViewState {
  const params = new URLSearchParams(search);
  const sortKey = SORT_KEYS.find((k) => k === params.get('sort')) ?? DEFAULT_SORT.key;
  const page = Number.parseInt(params.get('page') ?? '', 10);

  return {
    filters: {
      model: params.get('model') ?? '',
      status: parseStatus(params.get('status')),
      from: parseDate(params.get('from')),
      to: parseDate(params.get('to')),
    },
    sort: { key: sortKey, dir: params.get('dir') === 'asc' ? 'asc' : 'desc' },
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

/** Сериализация: значения по умолчанию в URL не попадают, чтобы ссылки были короткими. */
export function serializeViewState({ filters, sort, page }: ViewState): string {
  const params = new URLSearchParams();
  if (filters.model) params.set('model', filters.model);
  if (filters.status !== null) params.set('status', String(filters.status));
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
    params.set('sort', sort.key);
    params.set('dir', sort.dir);
  }
  if (page > 1) params.set('page', String(page));
  const query = params.toString();
  return query ? `?${query}` : '';
}
