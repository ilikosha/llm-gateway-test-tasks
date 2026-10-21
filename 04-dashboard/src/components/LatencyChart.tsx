import { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatMs, formatShortDateTime } from '../lib/format';
import { latencySeries } from '../lib/summary';
import type { RequestRecord } from '../types';

const BUCKET_MS = 3 * 3600 * 1000;

export function LatencyChart({ records }: { records: readonly RequestRecord[] }) {
  const data = useMemo(() => latencySeries(records, BUCKET_MS), [records]);

  return (
    <section className="card" aria-label="График задержки">
      <h2 className="m-0 mb-3 text-[1.05rem] font-semibold">Средняя задержка во времени</h2>
      {data.length === 0 ? (
        <p className="text-sm text-muted">Нет данных для выбранных фильтров</p>
      ) : (
        <div className="h-[220px] sm:h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--c-border))" />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={formatShortDateTime}
                tick={{ fontSize: 12, fill: 'rgb(var(--c-muted))' }}
                stroke="rgb(var(--c-border))"
                minTickGap={40}
              />
              <YAxis tickFormatter={(v: number) => `${v}`} unit=" мс" width={70} tick={{ fontSize: 12, fill: 'rgb(var(--c-muted))' }} stroke="rgb(var(--c-border))" />
              <Tooltip
                contentStyle={{ background: 'rgb(var(--c-surface))', border: '1px solid rgb(var(--c-border))', borderRadius: 6 }}
                labelStyle={{ color: 'rgb(var(--c-text))' }}
                itemStyle={{ color: 'rgb(var(--c-text))' }}
                labelFormatter={(value) => formatShortDateTime(Number(value))}
                formatter={(value) => [formatMs(Number(value)), 'Средняя задержка']}
              />
              <Line type="monotone" dataKey="avgLatencyMs" stroke="rgb(var(--c-accent))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
