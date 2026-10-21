import { describe, expect, it } from 'vitest';

import { DEFAULT_VIEW, parseViewState, serializeViewState } from './urlState';

describe('urlState', () => {
  it('parses an empty query to defaults', () => {
    expect(parseViewState('')).toEqual(DEFAULT_VIEW);
  });

  it('round-trips a full state', () => {
    const state = {
      filters: { model: 'gpt-4o', status: 429 as const, from: '2025-03-01', to: '2025-03-05' },
      sort: { key: 'latencyMs' as const, dir: 'asc' as const },
      page: 3,
    };
    expect(parseViewState(serializeViewState(state))).toEqual(state);
  });

  it('omits defaults from the URL', () => {
    expect(serializeViewState(DEFAULT_VIEW)).toBe('');
  });

  it('ignores invalid values', () => {
    const state = parseViewState('?status=418&from=garbage&sort=hack&page=-4&to=2025-13-45');
    expect(state).toEqual(DEFAULT_VIEW);
  });
});
