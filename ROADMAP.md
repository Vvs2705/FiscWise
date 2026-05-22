# FiscWise — Roadmap MVP

> Última atualização: 21/05/2026

---

## ✅ Fase 1 — Fundação (Concluído)

- [x] Arquitetura multi-tenant com `tenant_id` em todas as entidades
- [x] Autenticação JWT + Google OAuth
- [x] Registro em 3 passos (empresa → usuário → plano)
- [x] Middleware de tenant isolation
- [x] Lifespan handler FastAPI (sem deprecation warnings)
- [x] Migrações Alembic versionadas
- [x] `release_command` no Fly.io (migrations antes do boot)
- [x] Docker + Fly.io deploy estável

---

## ✅ Fase 2 — Módulos Operacionais (Concluído)

- [x] **Clientes**: CRUD completo + importação XLSX (read-excel-file, sem CVE)
- [x] **Documentos**: upload Supabase Storage + categorização
- [x] **Financeiro**: receitas/despesas + gráficos Recharts
- [x] **Prazos**: obrigações fiscais com status e alertas
- [x] **Certificados**: A1/A3 com controle de validade

---

## ✅ Fase 3 — Segurança & Qualidade (Concluído)

- [x] Auditoria de segurança completa (28 arquivos removidos)
- [x] Zero vulnerabilidades CVE (`npm audit` limpo)
- [x] ESLint 9 + flat config (sem deprecated packages)
- [x] Vite 6.4 (patch GHSA-67mh-4wv8-2f99)
- [x] Code splitting: React.lazy + Suspense + manualChunks
- [x] Bundle otimizado: maior chunk 393 kB (recharts)

---

## ✅ Fase 4 — Identidade & UX (Concluído)

- [x] Redesign visual completo com dark mode
- [x] Identidade FiscWise: logo, favicon, meta tags, SEO
- [x] Crédito Vstack Solutions
- [x] Animações Framer Motion
- [x] Sidebar com logo clicável → dashboard
- [x] Botões hero do dashboard funcionais

---

## ✅ Fase 5 — Perfil & Configurações (Concluído)

- [x] **Tab Perfil**: editar nome e telefone (PATCH /auth/me)
- [x] **Tab Escritório**: CNPJ, endereço, site, telefone (PATCH /auth/tenant)
- [x] **Tab Plano**: cards Free/Starter/Pro com troca em tempo real
- [x] **Tab Segurança**: troca de senha com validação
- [x] **Tab Pagamento**: estrutura preparada (em breve)
- [x] Campos `phone`, `plan_slug`, `address`, `website` nos models + migração
- [x] `updateUser` no Zustand com localStorage sync

---

## 🔄 Tier 1 — Próximas features MVP (alto impacto, baixo risco)

### Importação XLSX em Lote
- [ ] Processar múltiplas linhas (atualmente importa apenas row[0])
- [ ] Preview da planilha antes de importar
- [ ] Relatório de erros por linha
- **Estimativa**: 1 dia | **Risco**: baixo

### Filtros e Busca nas Tabelas
- [ ] Busca por nome/CNPJ em Clientes
- [ ] Filtros por status em Prazos e Documentos
- [ ] Filtro por período em Financeiro
- [ ] Ordenação por coluna
- **Estimativa**: 1-2 dias | **Risco**: baixo

### Notificações In-App
- [ ] Bell icon no header com contador
- [ ] Alertas de: prazo próximo, certificado vencendo, deadline atrasado
- [ ] Marcar como lida / limpar todas
- **Estimativa**: 2 dias | **Risco**: baixo-médio

### Recorrência de Prazos
- [ ] Campo de recorrência (mensal, trimestral, anual)
- [ ] Geração automática do próximo prazo ao concluir
- **Estimativa**: 1 dia | **Risco**: baixo

---

## 🔄 Tier 2 — Features de valor médio (2-3 semanas)

### Alertas por E-mail (Resend)
- [ ] Integração Resend API
- [ ] Template de e-mail para prazos próximos (3 dias antes)
- [ ] Template para certificados vencendo (30 dias antes)
- [ ] Configuração de preferências no settings
- **Estimativa**: 3 dias | **Risco**: médio

### Exportação PDF/Excel
- [ ] Relatório financeiro mensal em PDF
- [ ] Lista de clientes em Excel
- [ ] Relatório de prazos por período
- **Estimativa**: 2-3 dias | **Risco**: baixo-médio

### Templates de Prazos por Tipo de Empresa
- [ ] Simples Nacional: obrigações mensais pré-configuradas
- [ ] Lucro Presumido: set de obrigações específicas
- [ ] MEI: DAS, DASN-SIMEI
- **Estimativa**: 2 dias | **Risco**: baixo

### Paginação Backend
- [ ] Endpoint `/clients` com `?page=&limit=&search=`
- [ ] Cursor-based pagination para performance
- [ ] Adaptar frontend para paginação server-side
- **Estimativa**: 2 dias | **Risco**: baixo

---

## 🔄 Tier 3 — Features avançadas (pós-MVP estável)

### Multi-usuário / Colaboradores
- [ ] Convite de colaboradores por e-mail
- [ ] Papéis: Admin, Contador, Assistente
- [ ] Permissões por módulo
- **Estimativa**: 1 semana | **Risco**: alto (impacta auth)

### Portal do Cliente (read-only)
- [ ] Link único por cliente para acompanhar documentos e prazos
- [ ] Sem login necessário (token temporário por link)
- **Estimativa**: 3-4 dias | **Risco**: médio

### Billing Real (Stripe)
- [ ] Stripe Checkout para upgrade de plano
- [ ] Webhook para ativar/desativar features por plano
- [ ] Histórico de faturas
- [ ] Cancelamento de plano
- **Estimativa**: 1 semana | **Risco**: alto (dados financeiros)

### Log de Atividades
- [ ] Audit trail por tenant: quem fez o quê e quando
- [ ] Visualização por módulo
- **Estimativa**: 2 dias | **Risco**: baixo

### Relatórios Avançados
- [ ] Dashboard com métricas por período selecionável
- [ ] Comparativo mensal/anual
- [ ] Top clientes por receita
- **Estimativa**: 3 dias | **Risco**: baixo

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| ✅ | Concluído e em produção |
| 🔄 | Planejado / Em progresso |
| ⚠️ | Bloqueado ou dependente |

---

## Decisões Técnicas Pendentes

- [ ] Migrar Fly.io app ID de `contaflow` para `fiscwise` (risco: downtime)
- [ ] Definir plano de preços final (Free/Starter/Pro com limites reais)
- [ ] Domínio fiscwise.com.br — configurar DNS para Vercel e Fly.io
