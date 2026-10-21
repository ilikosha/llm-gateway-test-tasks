import { describe, expect, it } from 'vitest';

import { latencySeries, summarize } from './summary';
import { makeRecord } from './testData';

describe('summarize', () => {
  it('returns zeros for an empty set (no NaN)', () => {
    expect(summarize([])).toEqual({ total: 0, errorRate: 0, avgLatencyMs: 0, totalCostUsd: 0 });
  });

  it('computes count, error rate, average latency and total cost', () => {
    const summary = summarize([
      makeRecord({ id: 1, status: 200, latencyMs: 1000, costUsd: 0.25 }),
      makeRecord({ id: 2, status: 200, latencyMs: 2000, costUsd: 0.5 }),
      makeRecord({ id: 3, status: 429, latencyMs: 100, costUsd: 0 }),
      makeRecord({ id: 4, status: 500, latencyMs: 900, costUsd: 0 }),
    ]);
    expect(summary.total).toBe(4);
    expect(summary.errorRate).toBe(0.5);
    expect(summary.avgLatencyMs).toBe(1000);
    expect(summary.totalCostUsd).toBeCloseTo(0.75, 10);
  });

  it('reports zero error rate when all requests succeed', () => {
    expect(summarize([makeRecord(), makeRecord({ id: 2 })]).errorRate).toBe(0);
  });
});

describe('latencySeries', () => {
  const HOUR = 3600 * 1000;

  it('averages latency per bucket and sorts by time', () => {
    const series = latencySeries(
      [
        makeRecord({ id: 1, time: '2025-03-10T13:10:00.000Z', latencyMs: 300 }),
        makeRecord({ id: 2, time: '2025-03-10T10:05:00.000Z', latencyMs: 100 }),
        makeRecord({ id: 3, time: '2025-03-10T10:55:00.000Z', latencyMs: 200 }),
      ],
      HOUR,
    );
    expect(series).toEqual([
      { time: Date.parse('2025-03-10T10:00:00.000Z'), avgLatencyMs: 150, count: 2 },
      { time: Date.parse('2025-03-10T13:00:00.000Z'), avgLatencyMs: 300, count: 1 },
    ]);
  });

  it('returns an empty series for no records', () => {
    expect(latencySeries([], HOUR)).toEqual([]);
  });
});
