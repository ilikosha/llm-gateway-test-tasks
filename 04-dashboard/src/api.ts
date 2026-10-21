import { queryOptions } from '@tanstack/react-query';

import { isSimulatedError } from './lib/simulateError';
import type { RequestRecord } from './types';

/** Имитация сетевой задержки. */
const SIMULATED_DELAY_MS = 800;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export async function fetchRequests(): Promise<RequestRecord[]> {
  if (isSimulatedError(window.location.search)) {
    await sleep(SIMULATED_DELAY_MS);
    throw new Error('Сервер недоступен (имитация ошибки: simulateError=1)');
  }
  const [response] = await Promise.all([
    fetch(`${import.meta.env.BASE_URL}data/requests.json`),
    sleep(SIMULATED_DELAY_MS),
  ]);
  if (!response.ok) throw new Error(`Не удалось загрузить данные (HTTP ${response.status})`);
  return (await response.json()) as RequestRecord[];
}

export const requestsQuery = queryOptions({
  queryKey: ['requests'],
  queryFn: fetchRequests,
  staleTime: Infinity,
  retry: false, // ошибку показываем сразу, повтор — по кнопке
});
