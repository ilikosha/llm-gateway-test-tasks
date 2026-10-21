import { useMemo } from 'react';

import { formatInt, formatMs, formatPercent, formatUsd } from '../lib/format';
import { summarize } from '../lib/summary';
import type { RequestRecord } from '../types';

export function SummaryCards({ records }: { records: readonly RequestRecord[] }) {
  const summary = useMemo(() => summarize(records), [records]);

  const cards = [
    { label: 'Запросов', value: formatInt(summary.total) },
    { label: 'Доля ошибок', value: formatPercent(summary.errorRate) },
    { label: 'Средняя задержка', value: formatMs(summary.avgLatencyMs) },
    { label: 'Общая стоимость', value: formatUsd(summary.totalCostUsd) },
  ];

  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Сводка">
      {cards.map((card) => (
        <div key={card.label} className="card min-w-0">
          <div className="text-sm text-muted">{card.label}</div>
          <div className="mt-1 text-xl font-semibold tabular-nums sm:text-[1.6rem]">{card.value}</div>
        </div>
      ))}
    </section>
  );
}
