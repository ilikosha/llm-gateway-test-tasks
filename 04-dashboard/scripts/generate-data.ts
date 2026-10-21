/**
 * Генератор демо-данных: запросы к LLM API.
 * Запуск: npm run generate-data  → public/data/requests.json
 * Генерация детерминирована (seed), поэтому JSON воспроизводим.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import type { RequestRecord, StatusCode } from '../src/types.ts';

const RECORDS_COUNT = 620;
const DAYS = 14;
/** Фиксированный конец периода, чтобы результат не зависел от даты запуска. */
const PERIOD_END = Date.UTC(2026, 9, 20, 23, 59, 59);

interface ModelProfile {
  name: string;
  /** Доля трафика */
  weight: number;
  /** USD за 1M токенов */
  inputPricePerM: number;
  outputPricePerM: number;
  /** Базовая задержка + мс на выходной токен */
  baseLatencyMs: number;
  msPerOutputToken: number;
}

const MODELS: readonly ModelProfile[] = [
  { name: 'gpt-4o', weight: 0.3, inputPricePerM: 2.5, outputPricePerM: 10, baseLatencyMs: 450, msPerOutputToken: 4 },
  { name: 'gpt-4o-mini', weight: 0.3, inputPricePerM: 0.15, outputPricePerM: 0.6, baseLatencyMs: 250, msPerOutputToken: 2 },
  { name: 'claude-3-5-sonnet', weight: 0.2, inputPricePerM: 3, outputPricePerM: 15, baseLatencyMs: 550, msPerOutputToken: 5 },
  { name: 'claude-3-5-haiku', weight: 0.12, inputPricePerM: 0.8, outputPricePerM: 4, baseLatencyMs: 300, msPerOutputToken: 2.5 },
  { name: 'llama-3.1-70b', weight: 0.08, inputPricePerM: 0.9, outputPricePerM: 0.9, baseLatencyMs: 650, msPerOutputToken: 7 },
];

/** mulberry32 — маленький детерминированный PRNG. */
function createRng(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = createRng(1630);

const between = (min: number, max: number): number => min + rng() * (max - min);

/** Лог-нормальное распределение: длинный хвост, как у реальных токенов и задержек. */
function logNormal(median: number, sigma: number): number {
  const u = Math.max(rng(), Number.EPSILON);
  const gauss = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
  return median * Math.exp(sigma * gauss);
}

function pickModel(): ModelProfile {
  let roll = rng();
  for (const model of MODELS) {
    roll -= model.weight;
    if (roll <= 0) return model;
  }
  return MODELS[0]!;
}

function pickStatus(): StatusCode {
  const roll = rng();
  if (roll < 0.045) return 429;
  if (roll < 0.07) return 500;
  return 200;
}

/** Больше трафика в рабочие часы (UTC 06–18). */
function randomTimestamp(): number {
  for (;;) {
    const ts = PERIOD_END - rng() * DAYS * 24 * 3600 * 1000;
    const hour = new Date(ts).getUTCHours();
    const acceptance = hour >= 6 && hour < 18 ? 1 : 0.35;
    if (rng() < acceptance) return Math.floor(ts);
  }
}

const round = (value: number, digits: number): number => {
  const k = 10 ** digits;
  return Math.round(value * k) / k;
};

function buildRecord(timestamp: number): Omit<RequestRecord, 'id'> {
  const model = pickModel();
  const status = pickStatus();
  const inputTokens = Math.round(Math.min(logNormal(700, 0.9), 16000));
  const time = new Date(timestamp).toISOString();

  if (status === 429) {
    // Rate limit: ответ быстрый, токены не генерируются, не тарифицируется.
    return { time, model: model.name, status, inputTokens, outputTokens: 0, latencyMs: Math.round(between(30, 180)), costUsd: 0 };
  }

  if (status === 500) {
    // Серверная ошибка: часто упирается в таймаут, не тарифицируется.
    return { time, model: model.name, status, inputTokens, outputTokens: 0, latencyMs: Math.round(between(800, 9000)), costUsd: 0 };
  }

  const outputTokens = Math.max(1, Math.round(Math.min(logNormal(320, 0.8), 4096)));
  const latencyMs = Math.round(model.baseLatencyMs * between(0.7, 1.5) + outputTokens * model.msPerOutputToken * between(0.8, 1.3));
  const costUsd = round(
    (inputTokens * model.inputPricePerM + outputTokens * model.outputPricePerM) / 1_000_000,
    6,
  );
  return { time, model: model.name, status, inputTokens, outputTokens, latencyMs, costUsd };
}

const records: RequestRecord[] = Array.from({ length: RECORDS_COUNT }, () => randomTimestamp())
  .sort((a, b) => a - b)
  .map((timestamp, index) => ({ id: index + 1, ...buildRecord(timestamp) }));

const outFile = resolve(dirname(fileURLToPath(import.meta.url)), '../public/data/requests.json');
mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, `${JSON.stringify(records, null, 2)}\n`);

console.log(`Сгенерировано ${records.length} записей → ${outFile}`);
