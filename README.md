# FiscWise — A Central Fiscal do Contador Moderno

> Clientes, documentos, obrigações, e-CAC, notas fiscais, cobranças, guias, certificados e inteligência operacional integrados em um único sistema contábil de alta performance.

---

## 1. O que é o FiscWise

O FiscWise é um sistema operacional completo para contadores, focado em automatizar a rotina fiscal e financeira, eliminar controles paralelos e reduzir riscos fiscais. O sistema atua de forma nativa e integrada na emissão de documentos fiscais, monitoramento de pendências na Receita Federal, cobrança de honorários e envio de guias e obrigações.

## 2. Para quem é

- **Contadores Autônomos**: Para gerenciar carteiras de clientes com total controle, organizando prazos e notas sem planilhas paralelas.
- **Pequenos e Médios Escritórios**: Preparado para operações com controle granular de carteiras por responsáveis e isolamento total de dados.
- **BPO Financeiro/Contábil**: Escalável para alto volume de notas, guias e fechamento de obrigações mensais.

## 3. Módulos Principais

- **Notas Fiscais (NFS-e)**: Emissão direta, automação de honorários mensais e conciliação contábil-financeira automática.
- **Central e-CAC / Receita Federal**: Consulta automática de Situação Fiscal, Caixa Postal, certidões e controle de procurações eletrônicas via integração oficial.
- **Certificados Digitais (A1/A3)**: Cofre criptografado de chaves operacionais e monitoramento de validades com alertas automáticos.
- **Obrigações Fiscais**: Motor inteligente de calendarização fiscal orientado pelo regime tributário, CNAE, município e UF de cada cliente.
- **Guias, Impostos e Comprovantes**: Controle e conciliação de pagamentos de DAS, DARF, GPS e ISS, com verificação de pendências.
- **Portal do Cliente**: Área exclusiva para o cliente final enviar documentos, pagar guias e baixar notas fiscais.
- **WhatsApp e Comunicação**: Régua de cobrança e envio automático de lembretes e guias direto no canal mais utilizado pelos clientes.
- **IA Operacional**: Processamento de documentos, extração de metadados de guias e assistência contábil baseada em dados reais.

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
