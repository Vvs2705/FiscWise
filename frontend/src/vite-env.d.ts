/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_COMPANY_CNPJ?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
