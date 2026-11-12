import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

// Fila de trabalho em segundo plano (backend/app/services/job_queue.py).
// Sem tela aqui: a Frente C decide a UI.

export type JobStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled';

export interface BackgroundJob {
  id: string;
  kind: string;
  status: JobStatus;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  result: Record<string, unknown> | null;
  run_after: string | null;
  created_at: string;
  updated_at: string;
}

const FINISHED: JobStatus[] = ['done', 'failed', 'cancelled'];

/** Status de um job; consulta a cada 3 s enquanto não termina. */
export function useJob(id: string | null | undefined) {
  return useQuery({
    queryKey: ['jobs', id],
    queryFn: async () => (await api.get<BackgroundJob>(`/api/v1/jobs/${id}`)).data,
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && FINISHED.includes(status) ? false : 3000;
    },
  });
}

/** Jobs recentes do escritório (opcionalmente filtrados por status). */
export function useJobs(params: { status?: JobStatus; limit?: number } = {}) {
  return useQuery({
    queryKey: ['jobs', 'list', params.status ?? null, params.limit ?? 20],
    queryFn: async () =>
      (await api.get<BackgroundJob[]>('/api/v1/jobs', { params: { limit: 20, ...params } })).data,
  });
}
