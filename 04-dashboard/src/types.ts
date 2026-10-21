export const STATUS_CODES = [200, 429, 500] as const;
export type StatusCode = (typeof STATUS_CODES)[number];

export interface RequestRecord {
  id: number;
  /** ISO 8601, UTC */
  time: string;
  model: string;
  status: StatusCode;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
  /** Стоимость запроса в USD */
  costUsd: number;
}

export type SortKey = 'time' | 'latencyMs' | 'costUsd';
export type SortDir = 'asc' | 'desc';

export interface SortState {
  key: SortKey;
  dir: SortDir;
}

export interface Filters {
  /** Пустая строка = все модели */
  model: string;
  /** null = все статусы */
  status: StatusCode | null;
  /** YYYY-MM-DD, включительно (UTC) */
  from: string;
  /** YYYY-MM-DD, включительно (UTC) */
  to: string;
}

export interface Summary {
  total: number;
  errorRate: number;
  avgLatencyMs: number;
  totalCostUsd: number;
}
