import { describe, expect, it } from 'vitest';

import { EMPTY_FILTERS, filterRecords, hasActiveFilters, paginate, sortRecords, uniqueModels } from './filters';
import { makeRecord } from './testData';

const records = [
  makeRecord({ id: 1, model: 'gpt-4o', status: 200, time: '2025-03-09T23:59:59.000Z', latencyMs: 900, costUsd: 0.03 }),
  makeRecord({ id: 2, model: 'gpt-4o', status: 429, time: '2025-03-10T00:00:00.000Z', latencyMs: 50, costUsd: 0 }),
  makeRecord({ id: 3, model: 'claude-3-5-haiku', status: 500, time: '2025-03-10T18:30:00.000Z', latencyMs: 5000, costUsd: 0 }),
  makeRecord({ id: 4, model: 'claude-3-5-haiku', status: 200, time: '2025-03-11T00:00:00.000Z', latencyMs: 400, costUsd: 0.002 }),
];

const ids = (list: { id: number }[]) => list.map((r) => r.id);

describe('filterRecords', () => {
  it('returns everything for empty filters', () => {
    expect(ids(filterRecords(records, EMPTY_FILTERS))).toEqual([1, 2, 3, 4]);
  });

  it('filters by model', () => {
    expect(ids(filterRecords(records, { ...EMPTY_FILTERS, model: 'claude-3-5-haiku' }))).toEqual([3, 4]);
  });

  it('filters by status', () => {
    expect(ids(filterRecords(records, { ...EMPTY_FILTERS, status: 200 }))).toEqual([1, 4]);
  });

  it('treats the date range as inclusive on both ends (UTC days)', () => {
    const result = filterRecords(records, { ...EMPTY_FILTERS, from: '2025-03-10', to: '2025-03-10' });
    expect(ids(result)).toEqual([2, 3]);
  });

  it('supports open-ended ranges', () => {
    expect(ids(filterRecords(records, { ...EMPTY_FILTERS, from: '2025-03-11' }))).toEqual([4]);
    expect(ids(filterRecords(records, { ...EMPTY_FILTERS, to: '2025-03-09' }))).toEqual([1]);
  });

  it('combines filters with AND', () => {
    const result = filterRecords(records, { model: 'gpt-4o', status: 429, from: '2025-03-10', to: '' });
    expect(ids(result)).toEqual([2]);
  });

  it('returns an empty list when nothing matches and does not mutate input', () => {
    const copy = [...records];
    expect(filterRecords(records, { ...EMPTY_FILTERS, model: 'unknown' })).toEqual([]);
    expect(records).toEqual(copy);
  });
});

describe('sortRecords', () => {
  it('sorts by time in both directions', () => {
    expect(ids(sortRecords(records, { key: 'time', dir: 'asc' }))).toEqual([1, 2, 3, 4]);
    expect(ids(sortRecords(records, { key: 'time', dir: 'desc' }))).toEqual([4, 3, 2, 1]);
  });

  it('sorts by latency', () => {
    expect(ids(sortRecords(records, { key: 'latencyMs', dir: 'asc' }))).toEqual([2, 4, 1, 3]);
    expect(ids(sortRecords(records, { key: 'latencyMs', dir: 'desc' }))).toEqual([3, 1, 4, 2]);
  });

  it('sorts by cost with a stable tie-break by id', () => {
    expect(ids(sortRecords(records, { key: 'costUsd', dir: 'asc' }))).toEqual([2, 3, 4, 1]);
    expect(ids(sortRecords(records, { key: 'costUsd', dir: 'desc' }))).toEqual([1, 4, 2, 3]);
  });

  it('does not mutate the input', () => {
    const copy = [...records];
    sortRecords(records, { key: 'latencyMs', dir: 'desc' });
    expect(records).toEqual(copy);
  });
});

describe('paginate', () => {
  const items = Array.from({ length: 45 }, (_, i) => i + 1);

  it('returns the requested page', () => {
    const page = paginate(items, 2, 20);
    expect(page.items[0]).toBe(21);
    expect(page.items).toHaveLength(20);
    expect(page.pageCount).toBe(3);
  });

  it('returns a partial last page', () => {
    expect(paginate(items, 3, 20).items).toEqual([41, 42, 43, 44, 45]);
  });

  it('clamps out-of-range pages', () => {
    expect(paginate(items, 99, 20).page).toBe(3);
    expect(paginate(items, 0, 20).page).toBe(1);
    expect(paginate(items, Number.NaN, 20).page).toBe(1);
  });

  it('handles an empty list', () => {
    expect(paginate([], 1, 20)).toEqual({ items: [], page: 1, pageCount: 1 });
  });
});

describe('uniqueModels', () => {
  it('returns sorted unique model names', () => {
    expect(uniqueModels(records)).toEqual(['claude-3-5-haiku', 'gpt-4o']);
  });
});

describe('hasActiveFilters', () => {
  it('false для пустых фильтров', () => {
    expect(hasActiveFilters(EMPTY_FILTERS)).toBe(false);
  });
  it('true, если задан любой фильтр', () => {
    expect(hasActiveFilters({ ...EMPTY_FILTERS, model: 'gpt-4o' })).toBe(true);
    expect(hasActiveFilters({ ...EMPTY_FILTERS, status: 429 })).toBe(true);
    expect(hasActiveFilters({ ...EMPTY_FILTERS, from: '2025-03-01' })).toBe(true);
    expect(hasActiveFilters({ ...EMPTY_FILTERS, to: '2025-03-01' })).toBe(true);
  });
});
