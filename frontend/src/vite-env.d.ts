/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  /** Destino opcional do RUM de Web Vitals (src/lib/vitals.ts). */
  readonly VITE_VITALS_ENDPOINT?: string;
  /** Token do Cloudflare Web Analytics; injetado no index.html só no build (vite.config.ts). */
  readonly VITE_CF_BEACON_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
