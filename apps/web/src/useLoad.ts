import { useEffect, useState } from 'react';
import { isAbort, request } from './api';

export function useLoad<T>(path: string | null, revision = 0, retain = false) {
  const [state, setState] = useState<{
    path: string;
    revision: number;
    data?: T;
    error?: unknown;
  }>();
  useEffect(() => {
    if (path === null) return;
    const controller = new AbortController();
    setState((previous) => ({
      path,
      revision,
      data: retain && previous?.path === path ? previous.data : undefined,
    }));
    request<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState({ path, revision, data });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted && !isAbort(error))
          setState((previous) => ({
            path,
            revision,
            error,
            data: retain && previous?.path === path ? previous.data : undefined,
          }));
      });
    return () => controller.abort();
  }, [path, revision, retain]);
  // Schon beim ersten Render eines neuen Pfads dürfen alte Daten nicht erscheinen.
  return state?.path === path && (retain || state.revision === revision)
    ? { data: state.data, error: state.error }
    : { data: undefined, error: undefined };
}
