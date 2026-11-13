/** Endereço da API. Mesmo valor para o app (axios) e para páginas estáticas como /precos. */
export const API_URL: string =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : 'https://fiscwise-api-45ckqevl6a-rj.a.run.app');
