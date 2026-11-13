import { api } from './api';

/**
 * Exportação LGPD: baixa GET /api/v1/account/export como
 * `fiscwise-dados-AAAA-MM-DD.json`. Liberada também com a conta só para
 * leitura (teste ou período pago acabou), para o cliente levar seus dados.
 */
export async function downloadMyDataExport(): Promise<void> {
  const { data } = await api.get('/api/v1/account/export');
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `fiscwise-dados-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
