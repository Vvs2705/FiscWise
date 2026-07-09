# FiscWise — A Central Fiscal do Contador Moderno

> Clientes, documentos, obrigações, e-CAC, notas fiscais, cobranças, guias, certificados e inteligência operacional integrados em um único sistema contábil de alta performance.

---

## 1. O que é o FiscWise

O FiscWise é a central operacional do contador: organiza a carteira de clientes, documentos, obrigações, guias, honorários e o fechamento mensal em um único sistema, com IA fiscal de apoio. Elimina controles paralelos (planilhas) e reduz risco de perda de prazo.

As **integrações governamentais** (emissão NFS-e, consulta e-CAC/Receita, Caixa Postal SERPRO, envio WhatsApp oficial) estão no roadmap e dependem de credenciais/contratos externos — o estado atual de cada módulo está marcado na tabela abaixo. O FiscWise **não** apresenta dado governamental simulado como oficial em produção.

## 2. Para quem é

- **Contadores Autônomos**: Para gerenciar carteiras de clientes com total controle, organizando prazos e notas sem planilhas paralelas.
- **Pequenos e Médios Escritórios**: Preparado para operações com controle granular de carteiras por responsáveis e isolamento total de dados.
- **BPO Financeiro/Contábil**: Escalável para alto volume de notas, guias e fechamento de obrigações mensais.

## 3. Módulos e estado atual

Legenda: ✅ operacional · 🟡 parcial (função existe, sem automação externa) · 🛠️ roadmap (requer credencial/contrato externo)

| Módulo | Estado | O que faz hoje |
|---|---|---|
| **Clientes / Documentos / Financeiro** | ✅ | Carteira multi-tenant, upload de documentos (Supabase Storage), contas a receber e inadimplência. |
| **Obrigações Fiscais** | ✅ | Motor de calendarização por regime/CNAE/município/UF, recorrência e prazos. |
| **Fechamento Mensal + Dossiê PDF** | ✅ | Fechamento por competência com geração real de dossiê em PDF. |
| **IA Operacional** | ✅ | Calculadora fiscal e assistente por IA (requer `OPENAI_API_KEY`). |
| **Portal do Cliente** | ✅ | Área do cliente final (magic-link/convite) para documentos e guias. |
| **Guias (DAS/DARF/GPS/ISS)** | 🟡 | Registro, conciliação de pagamento e comprovantes. **Não** gera a guia via PGDAS nem verifica pendência na Receita automaticamente. |
| **Certificados Digitais (A1/A3)** | 🟡 | Cadastro e alerta de validade. Ainda **não** é cofre que armazena/assina com a chave. |
| **Caixa Postal Fiscal (e-CAC/DTE)** | 🛠️ | Cliente SERPRO Integra Contador implementado, **desligado por padrão** — requer contrato SERPRO + e-CNPJ + mTLS. |
| **Notas Fiscais (NFS-e)** | 🛠️ | Cadastro/gestão prontos; **emissão real depende de homologação** na prefeitura/Portal Nacional (hoje usa provider de simulação). |
| **Central e-CAC / Situação Fiscal** | 🛠️ | Depende do contrato SERPRO (mesma credencial da Caixa Postal). |
| **Monitor Fiscal** | 🛠️ | Consulta automática à Receita depende de integração oficial (SERPRO). |
| **WhatsApp e Comunicação** | 🛠️ | Régua de cobrança modelada; envio real requer WhatsApp Business API oficial (Meta/BSP). |

---

## 4. Stack Tecnológica

### Backend
- **Python 3.14+**
- **FastAPI** — Framework web assíncrono de alta performance
- **SQLAlchemy 2.x (async)** & **asyncpg** — ORM assíncrono para PostgreSQL
- **Alembic** — Gerenciamento e versionamento de migrações do banco
- **Supabase** — PostgreSQL gerenciado + Storage para arquivos privados
- **Redis** — Cache, filas e rate limiting estrito
- **Pydantic v2** — Validação estrita de contratos e schemas de dados

### Frontend
- **React 18** & **TypeScript 5.5+** (Strict mode)
- **Vite 6.4+** — Build tool rápido e otimizado
- **Tailwind CSS 3** — Estilização moderna e responsiva
- **React Router v6** — Roteamento de Single Page Application (SPA)
- **TanStack Query v5** — Gerenciamento de estado de servidor e cache
- **Zustand** — Gerenciamento de estado global leve e reativo
- **React Hook Form** & **Zod** — Validação e processamento de formulários

---

## 5. Desenvolvimento Local

### Backend (FastAPI)

1. Entre no diretório do backend:
   ```bash
   cd backend
   ```
2. Crie e ative o ambiente virtual Python:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente baseando-se no arquivo `.env.example`.
5. Execute o servidor de desenvolvimento:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend (React + Vite)

1. Entre no diretório do frontend:
   ```bash
   cd frontend
   ```
2. Instale as dependências:
   ```bash
   npm install
   ```
3. Execute o servidor de desenvolvimento:
   ```bash
   npm run dev
   ```

---

## 6. Variáveis de Ambiente

As configurações do sistema são controladas pelas seguintes variáveis no arquivo `.env` (consulte `.env.example` para obter detalhes):

### Backend (`backend/.env.example`)
- `DATABASE_URL`: URI de conexão assíncrona com o PostgreSQL (ex: `postgresql+asyncpg://...`).
- `JWT_SECRET_KEY`: Chave para geração e validação de tokens JWT.
- `SUPABASE_URL`: Endpoint da API do projeto Supabase.
- `SUPABASE_SECRET_KEY`: Chave de serviço (Service Role Key) para operações com arquivos.
- `GOOGLE_CLIENT_ID`: ID de cliente do Google OAuth para autenticação social.
- `ALLOWED_ORIGINS`: Domínios autorizados a consumir a API (CORS).

### Frontend (`frontend/.env.example`)
- `VITE_API_URL`: URL base do backend (ex: `http://localhost:8000`).
- `VITE_GOOGLE_CLIENT_ID`: Chave correspondente para autenticação Google OAuth.

---

## 7. Como Executar Testes

### Backend (pytest)
```bash
cd backend
pytest tests/ -v
```

### Frontend (Build & Tipagem)
```bash
cd frontend
npm run build
```

---

## 8. Deploy

### Backend (Fly.io)
O deploy é realizado via CLI do Fly.io, utilizando o arquivo de configuração `fly.toml`. As migrações do Alembic são aplicadas de forma totalmente automatizada antes do startup das máquinas através do comando de release configurado.
```bash
fly deploy
```

### Frontend (Vercel)
O frontend está integrado à Vercel para deploys contínuos. Para subir builds manuais:
```bash
vercel --prod
```

---

## 9. Segurança e Isolamento Multi-Tenant

O FiscWise foi arquitetado com isolamento rígido multi-tenant, garantindo que usuários de diferentes empresas contábeis nunca compartilhem ou acessem dados de terceiros. Para detalhes das políticas de segurança, histórico de auditoria e configurações de segurança de produção, acesse [docs/SECURITY_CORRECTIONS.md](file:///c:/Users/VINICIUS/Videos/MEUS%20PROJETOS/FiscWise/docs/SECURITY_CORRECTIONS.md).
