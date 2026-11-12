import { useCallback } from 'react';
import axios from 'axios';
import { useLiveQuery } from 'dexie-react-hooks';
import { useLocalDb, useSyncStatus } from '@/lib/offline/hooks';
import { requestInvoiceEmission } from '@/lib/offline/repositories';
import type { InvoiceResponse } from '../services/invoices.service';

/** Texto obrigatório (OFFLINE_SYNC.md, seção 6): offline o FiscWise não emite. */
export const OFFLINE_EMISSION_NOTICE =
  'Sem internet a nota não é emitida: a autorização depende da SEFAZ/prefeitura. Ela ficará como Pendente de transmissão e será enviada quando a conexão voltar.';

export const OFFLINE_CANCEL_NOTICE =
  'Precisa de internet: o cancelamento depende da SEFAZ/prefeitura e não pode ser feito sem conexão.';

/** Erro sem resposta do servidor (rede caiu durante a chamada). */
export function isNetworkError(error: unknown): boolean {
  return axios.isAxiosError(error) && !error.response;
}

/**
 * Emissão offline-aware: sem rede, o pedido vai para a outbox como
 * `emit_requested` e a nota fica "Pendente de transmissão" (só local).
 */
export function useOfflineEmission(invoice: InvoiceResponse | undefined) {
  const { isOffline } = useSyncStatus();
  const db = useLocalDb();
  const id = invoice?.id;
  const localStatus = useLiveQuery(
    async () => (db && id ? (await db.invoices.get(id))?.status : undefined),
    [db, id],
  );

  const serverStatus = invoice?.status;
  const pendingTransmission =
    localStatus === 'pending_transmission' && (serverStatus === 'draft' || serverStatus === 'rejected');

  /** Status a exibir: o local só prevalece enquanto o servidor não avançou. */
  const displayStatus = pendingTransmission ? 'pending_transmission' : serverStatus;

  const enqueueEmission = useCallback(async () => {
    if (!db || !invoice) throw new Error('Banco local indisponível.');
    await requestInvoiceEmission(db, invoice.id, invoice);
  }, [db, invoice]);

  return { isOffline, canQueue: !!db, pendingTransmission, displayStatus, enqueueEmission };
}
