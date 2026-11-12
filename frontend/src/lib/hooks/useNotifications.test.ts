import { describe, expect, it } from 'vitest';
import { describeClientEmailResult, type ClientEmailResult } from './useNotifications';

const base: ClientEmailResult = {
  queued: false,
  sent: false,
  status: 'skipped',
  reason: null,
  recipient: 'cliente@exemplo.com',
  notification_id: 'n1',
  message: '',
};

describe('describeClientEmailResult', () => {
  it('sucesso só quando o provedor aceitou', () => {
    expect(describeClientEmailResult({ ...base, sent: true, status: 'sent', message: 'Enviado.' })).toEqual({
      kind: 'success',
      message: 'Enviado.',
    });
  });

  it('e-mail desligado vira aviso com o que configurar', () => {
    const t = describeClientEmailResult({ ...base, reason: 'email_disabled' });
    expect(t.kind).toBe('warning');
    expect(t.message).toContain('RESEND_ENABLED');
  });

  it('cliente sem e-mail vira aviso', () => {
    expect(describeClientEmailResult({ ...base, reason: 'no_recipient' }).kind).toBe('warning');
  });

  it('falha do provedor vira erro', () => {
    const t = describeClientEmailResult({ ...base, status: 'failed', reason: 'provider_error', message: 'Recusado.' });
    expect(t).toEqual({ kind: 'error', message: 'Recusado.' });
  });
});
