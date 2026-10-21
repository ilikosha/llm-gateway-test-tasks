import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import { requestsQuery } from './api';
import { FiltersBar } from './components/FiltersBar';
import { LatencyChart } from './components/LatencyChart';
import { RequestsTable } from './components/RequestsTable';
import { EmptyState, ErrorState, LoadingSkeleton } from './components/StateViews';
import { SummaryCards } from './components/SummaryCards';
import { ThemeToggle } from './components/ThemeToggle';
import { filterRecords, hasActiveFilters, uniqueModels } from './lib/filters';
import { DEFAULT_VIEW } from './lib/urlState';
import { useTheme } from './useTheme';
import { useViewState } from './useViewState';

const PAGE_SIZE = 20;

export function App() {
  const { data, isPending, error, refetch, isFetching } = useQuery(requestsQuery);
  const [view, updateView] = useViewState();
  const [theme, toggleTheme] = useTheme();

  const records = useMemo(() => data ?? [], [data]);
  const models = useMemo(() => uniqueModels(records), [records]);
  const filtered = useMemo(() => filterRecords(records, view.filters), [records, view.filters]);

  const resetFilters = () => updateView((prev) => ({ ...prev, filters: DEFAULT_VIEW.filters, page: 1 }));

  return (
    <div className="mx-auto max-w-[1100px] p-3 sm:p-4">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="m-0 mb-1 text-2xl font-bold">LLM Requests Dashboard</h1>
          <p className="text-sm text-muted">Мониторинг запросов к LLM API: задержки, ошибки и стоимость</p>
        </div>
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </header>

      {error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} retrying={isFetching} />
      ) : isPending ? (
        <LoadingSkeleton />
      ) : (
        <main className="grid grid-cols-[minmax(0,1fr)] gap-4">
          <FiltersBar
            filters={view.filters}
            models={models}
            onChange={(filters) => updateView((prev) => ({ ...prev, filters, page: 1 }))}
            onReset={resetFilters}
          />
          {filtered.length === 0 ? (
            <EmptyState onReset={hasActiveFilters(view.filters) ? resetFilters : undefined} />
          ) : (
            <>
              <SummaryCards records={filtered} />
              <LatencyChart records={filtered} />
              <RequestsTable
                records={filtered}
                sort={view.sort}
                page={view.page}
                pageSize={PAGE_SIZE}
                onSortChange={(sort) => updateView((prev) => ({ ...prev, sort, page: 1 }))}
                onPageChange={(page) => updateView((prev) => ({ ...prev, page }))}
              />
            </>
          )}
        </main>
      )}
    </div>
  );
}
