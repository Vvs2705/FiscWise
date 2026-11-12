import type { ReactNode } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';

const GOOGLE_CLIENT_ID: string = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '';

/**
 * Provider do login com Google, montado só nas rotas que usam `GoogleLogin`
 * (/login e /register). O provider injeta o script accounts.google.com/gsi/client
 * (~100 kB); fora dessas rotas ele não é baixado.
 *
 * Sem VITE_GOOGLE_CLIENT_ID as páginas não renderizam o botão do Google, então
 * o provider (e o script) também não são montados.
 */
export default function GoogleAuthProvider({ children }: { children: ReactNode }) {
  if (!GOOGLE_CLIENT_ID) return <>{children}</>;
  return <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>{children}</GoogleOAuthProvider>;
}
