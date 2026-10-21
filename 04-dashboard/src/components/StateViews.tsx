interface EmptyProps {
  onReset?: () => void;
}

export function EmptyState({ onReset }: EmptyProps) {
  return (
    <section className="card grid justify-items-center gap-3 px-4 py-12 text-center" aria-label="Нет данных">
      <div className="text-3xl" aria-hidden="true">
        🔍
      </div>
      <h2 className="m-0 text-lg font-semibold">Ничего не найдено</h2>
      <p className="max-w-sm text-sm text-muted">По выбранным фильтрам нет ни одного запроса. Измените условия или сбросьте фильтры.</p>
      {onReset && (
        <button type="button" className="btn" onClick={onReset}>
          Сбросить фильтры
        </button>
      )}
    </section>
  );
}

interface ErrorProps {
  message: string;
  onRetry: () => void;
  retrying?: boolean;
}

export function ErrorState({ message, onRetry, retrying = false }: ErrorProps) {
  return (
    <div className="card grid justify-items-center gap-3 px-4 py-12 text-center text-err" role="alert">
      <h2 className="m-0 text-lg font-semibold">Не удалось загрузить данные</h2>
      <p className="text-sm">{message}</p>
      <button type="button" className="btn" onClick={onRetry} disabled={retrying}>
        {retrying ? 'Загрузка…' : 'Повторить'}
      </button>
    </div>
  );
}

const bar = 'animate-pulse rounded-md bg-line';

export function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-4" role="status" aria-label="Загрузка данных">
      <div className="card h-[72px]">
        <div className={`${bar} h-full`} />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="card grid gap-2">
            <div className={`${bar} h-4 w-2/3`} />
            <div className={`${bar} h-8 w-1/2`} />
          </div>
        ))}
      </div>
      <div className="card">
        <div className={`${bar} h-[260px]`} />
      </div>
      <div className="card grid gap-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className={`${bar} h-8`} />
        ))}
      </div>
      <span className="sr-only">Загрузка данных…</span>
    </div>
  );
}
