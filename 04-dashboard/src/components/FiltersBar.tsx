import { STATUS_CODES } from '../types';
import type { Filters, StatusCode } from '../types';

interface Props {
  filters: Filters;
  models: readonly string[];
  onChange: (filters: Filters) => void;
  onReset: () => void;
}

export function FiltersBar({ filters, models, onChange, onReset }: Props) {
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });

  return (
    <section className="card grid grid-cols-1 items-end gap-3 min-[480px]:grid-cols-2 lg:grid-cols-5" aria-label="Фильтры">
      <label className="grid gap-1 text-sm text-muted">
        Модель
        <select value={filters.model} onChange={(e) => set('model', e.target.value)}>
          <option value="">Все</option>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </label>

      <label className="grid gap-1 text-sm text-muted">
        Статус
        <select
          value={filters.status ?? ''}
          onChange={(e) => set('status', e.target.value ? (Number(e.target.value) as StatusCode) : null)}
        >
          <option value="">Все</option>
          {STATUS_CODES.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </label>

      <label className="grid gap-1 text-sm text-muted">
        С даты
        <input type="date" value={filters.from} max={filters.to || undefined} onChange={(e) => set('from', e.target.value)} />
      </label>

      <label className="grid gap-1 text-sm text-muted">
        По дату
        <input type="date" value={filters.to} min={filters.from || undefined} onChange={(e) => set('to', e.target.value)} />
      </label>

      <button type="button" className="btn btn-secondary" onClick={onReset}>
        Сбросить
      </button>
    </section>
  );
}
