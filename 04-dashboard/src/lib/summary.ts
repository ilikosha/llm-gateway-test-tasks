import type { RequestRecord, Summary } from '../types';

const isError = (record: RequestRecord): boolean => record.status >= 400;

/** Сводка по набору записей. Для пустого набора все значения равны 0. */
export function summarize(records: readonly RequestRecord[]): Summary {
  const total = records.length;
  if (total === 0) return { total: 0, errorRate: 0, avgLatencyMs: 0, totalCostUsd: 0 };

  let errors = 0;
  let latencySum = 0;
  let cost = 0;
  for (const record of records) {
    if (isError(record)) errors += 1;
    latencySum += record.latencyMs;
    cost += record.costUsd;
  }

  return {
    total,
    errorRate: errors / total,
    avgLatencyMs: latencySum / total,
    totalCostUsd: cost,
  };
}

export interface LatencyPoint {
  /** Начало часового интервала, ms since epoch (UTC) */
  time: number;
  avgLatencyMs: number;
  count: number;
}

/** Средняя задержка по бакетам фиксированной ширины, по возрастанию времени. */
export function latencySeries(records: readonly RequestRecord[], bucketMs: number): LatencyPoint[] {
  const buckets = new Map<number, { sum: number; count: number }>();
  for (const record of records) {
    const bucket = Math.floor(Date.parse(record.time) / bucketMs) * bucketMs;
    const acc = buckets.get(bucket) ?? { sum: 0, count: 0 };
    acc.sum += record.latencyMs;
    acc.count += 1;
    buckets.set(bucket, acc);
  }
  return [...buckets]
    .sort(([a], [b]) => a - b)
    .map(([time, { sum, count }]) => ({ time, avgLatencyMs: Math.round(sum / count), count }));
}
