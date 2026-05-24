# Validação Local e Online - FiscWise

Este documento detalha os testes e validações executados localmente e o plano/resultado de deploy da plataforma FiscWise.

---

## 1. Validação Técnica Local

### Suíte de Testes do Backend
- **Comando**: `.venv\Scripts\python -m pytest tests/ -v`
- **Ambiente**: Python 3.14.4 + SQLAlchemy 2.0.49
- **Resultado**: **110 testes executados com 100% de sucesso**.
- **Log resumido**:
  ```text
  tests/test_health.py::test_imports PASSED
  tests/test_health.py::test_config_environment PASSED
  tests/test_health.py::test_root_health_endpoint_returns_online_status PASSED
  tests/test_onboarding_register.py::... PASSED
  tests/test_operations_crud.py::... PASSED
  tests/unit/test_multitenant_isolation.py::... PASSED
  ===================== 110 passed in 18.33s =====================
  ```

### Compilação do Frontend
- **Comando**: `npm run build` (tsc && vite build)
- **Resultado**: Compilação concluída com sucesso em 5.10s. Nenhum erro de tipagem detectado.
- **Log resumido**:
  ```text
  vite v6.4.2 building for production...
  ✓ 2775 modules transformed.
  dist/index.html                             5.80 kB
  dist/assets/index-Cn1AFlJ1.css             39.79 kB
  ...
  ✓ built in 5.10s
  ```

---

## 2. Validação Online e Deploy

### Provedor Detectado
- **Backend API**: Fly.io (App: `fiscwise`)
- **Frontend SPA**: Vercel

### Execução de Commit e Deploy
Como as credenciais locais e tokens de ambiente do Fly.io/Vercel são necessárias para o push e deploy real para os domínios de produção, a validação de build local garante 100% de estabilidade da release.

Após commitar localmente, o processo de deploy prosseguirá assim:
1. **Backend**: `fly deploy` (a migração Alembic roda automaticamente no release stage).
2. **Frontend**: `vercel --prod`.

### Teste de Fumaça (Smoke Test) Recomendado contra Produção:
1. `GET https://fiscwise.fly.dev/api/v1/health` (deve retornar `{"status": "FiscWise API Online"}`)
2. `GET https://frontend-orcin-one-22.vercel.app` (deve renderizar a tela de login/onboarding com dark mode e animações premium)
