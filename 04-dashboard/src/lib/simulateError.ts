/** Включает демо-ошибку загрузки: `?simulateError=1` (или `true`). */
export function isSimulatedError(search: string): boolean {
  const value = new URLSearchParams(search).get('simulateError');
  return value === '1' || value === 'true';
}
