import type { RequestRecord } from '../types';

export function makeRecord(overrides: Partial<RequestRecord> = {}): RequestRecord {
  return {
    id: 1,
    time: '2025-03-10T12:00:00.000Z',
    model: 'gpt-4o',
    status: 200,
    inputTokens: 100,
    outputTokens: 50,
    latencyMs: 1000,
    costUsd: 0.01,
    ...overrides,
  };
}
