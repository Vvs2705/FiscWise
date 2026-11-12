import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { initMonitoring } from './lib/monitoring'
import './index.css'

// O GoogleOAuthProvider não envolve mais o app inteiro: ele injeta o script
// do Google (~100 kB) e só /login e /register precisam dele (ver App.tsx).

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// Sentry carrega depois da montagem, em tempo ocioso (lib/monitoring.ts).
initMonitoring()
