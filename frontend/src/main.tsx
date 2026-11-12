import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { initMonitoring } from './lib/monitoring'
import './index.css'

// O GoogleOAuthProvider não envolve mais o app inteiro: ele injeta o script
// do Google (~100 kB) e só /login e /register precisam dele (ver App.tsx).

// Web Vitals (RUM): chunk separado, baixado só depois do `load` para não
// competir com o caminho crítico. Sem VITE_VITALS_ENDPOINT no build de
// produção o bloco é removido (nenhum byte a mais).
if (import.meta.env.VITE_VITALS_ENDPOINT || import.meta.env.DEV) {
  const loadVitals = () => {
    import('./lib/vitals').then((m) => m.startVitals()).catch(() => {})
  }
  if (document.readyState === 'complete') loadVitals()
  else addEventListener('load', loadVitals, { once: true })
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// Sentry carrega depois da montagem, em tempo ocioso (lib/monitoring.ts).
initMonitoring()
