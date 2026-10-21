import { useMemo } from 'react';

import { formatDateTime, formatInt, formatMs, formatUsd } from '../lib/format';
import { paginate, sortRecords } from '../lib/filters';
import type { RequestRecord, SortKey, SortState } from '../types';

const th = 'border-b border-line px-2.5 py-2 font-semibold text-muted';
const td = 'border-b border-line px-2.5 py-2';
const badge = 'inline-block rounded-full px-2 py-0.5 text-[0.8rem] font-semibold';

interface Props {
  records: readonly RequestRecord[];
  sort: SortState;
  page: number;
  pageSize: number;
  onSortChange: (sort: SortState) => void;
  onPageChange: (page: number) => void;
}

export function RequestsTable({ records, sort, page, pageSize, onSortChange, onPageChange }: Props) {
  const sorted = useMemo(() => sortRecords(records, sort), [records, sort]);
  const current = paginate(sorted, page, pageSize);

  const toggleSort = (key: SortKey) =>
    onSortChange({ key, dir: sort.key === key && sort.dir === 'desc' ? 'asc' : 'desc' });

  const sortableHeader = (key: SortKey, label: string, numeric = false) => (
    <th
      className={`${th} ${numeric ? 'text-right' : 'text-left'}`}
      aria-sort={sort.key === key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <button type="button" className="cursor-pointer border-0 bg-transparent p-0 font-[inherit] text-inherit" onClick={() => toggleSort(key)}>
        {label}
        <span aria-hidden="true">{sort.key === key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}</span>
      </button>
    </th>
  );

  return (
    <section className="card" aria-label="Таблица запросов">
      <h2 className="m-0 mb-3 text-[1.05rem] font-semibold">Запросы</h2>
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="w-full whitespace-nowrap border-collapse text-[0.9rem]">
          <thead>
            <tr>
              {sortableHeader('time', 'Время (UTC)')}
              <th className={`${th} text-left`}>Модель</th>
              <th className={`${th} text-left`}>Статус</th>
              <th className={`${th} text-right`}>Токены in</th>
              <th className={`${th} text-right`}>Токены out</th>
              {sortableHeader('latencyMs', 'Задержка', true)}
              {sortableHeader('costUsd', 'Стоимость', true)}
            </tr>
          </thead>
          <tbody>
            {current.items.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-6 text-center text-sm text-muted">
                  Нет записей для выбранных фильтров
                </td>
              </tr>
            ) : (
              current.items.map((r) => (
                <tr key={r.id}>
                  <td className={td}>{formatDateTime(r.time)}</td>
                  <td className={td}>{r.model}</td>
                  <td className={td}>
                    <span className={`${badge} ${r.status === 200 ? 'bg-ok-bg text-ok' : 'bg-err-bg text-err'}`}>{r.status}</span>
                  </td>
                  <td className={`${td} text-right tabular-nums`}>{formatInt(r.inputTokens)}</td>
                  <td className={`${td} text-right tabular-nums`}>{formatInt(r.outputTokens)}</td>
                  <td className={`${td} text-right tabular-nums`}>{formatMs(r.latencyMs)}</td>
                  <td className={`${td} text-right tabular-nums`}>{formatUsd(r.costUsd, 4)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <nav className="mt-3 flex flex-wrap items-center justify-center gap-2 text-[0.9rem] sm:justify-between" aria-label="Пагинация">
        <button type="button" className="btn btn-secondary" disabled={current.page <= 1} onClick={() => onPageChange(current.page - 1)}>
          Назад
        </button>
        <span>
          Страница {current.page} из {current.pageCount} · {formatInt(records.length)} записей
        </span>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={current.page >= current.pageCount}
          onClick={() => onPageChange(current.page + 1)}
        >
          Вперёд
        </button>
      </nav>
    </section>
  );
}
