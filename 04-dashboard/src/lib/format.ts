const intFormat = new Intl.NumberFormat('ru-RU');
const dateTimeFormat = new Intl.DateTimeFormat('ru-RU', {
  dateStyle: 'short',
  timeStyle: 'medium',
  timeZone: 'UTC',
});
const shortDateTimeFormat = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
});

export const formatInt = (value: number): string => intFormat.format(Math.round(value));
export const formatMs = (value: number): string => `${formatInt(value)} мс`;
export const formatPercent = (ratio: number): string => `${(ratio * 100).toFixed(1)}%`;
export const formatUsd = (value: number, digits = 2): string => `$${value.toFixed(digits)}`;
export const formatDateTime = (iso: string): string => dateTimeFormat.format(new Date(iso));
export const formatShortDateTime = (ms: number): string => shortDateTimeFormat.format(new Date(ms));
