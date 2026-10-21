import { useCallback, useEffect, useState } from 'react';

import { parseViewState, serializeViewState } from './lib/urlState';
import type { ViewState } from './lib/urlState';

type Updater = (prev: ViewState) => ViewState;

/**
 * Состояние страницы (фильтры, сортировка, страница), синхронизированное с query-параметрами URL.
 * Изменения пишутся через replaceState, чтобы не засорять историю; popstate подхватывает ручной переход.
 */
export function useViewState(): [ViewState, (update: Updater) => void] {
  const [state, setState] = useState(() => parseViewState(window.location.search));

  useEffect(() => {
    const onPopState = () => setState(parseViewState(window.location.search));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const update = useCallback((updater: Updater) => {
    setState((prev) => {
      const next = updater(prev);
      const url = `${window.location.pathname}${serializeViewState(next)}${window.location.hash}`;
      window.history.replaceState(null, '', url);
      return next;
    });
  }, []);

  return [state, update];
}
