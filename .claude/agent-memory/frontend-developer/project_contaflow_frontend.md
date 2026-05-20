---
name: contaflow-frontend-architecture
description: Arquitetura e estado atual do frontend ContaFlow (SaaS para contadores)
metadata:
  type: project
---

Frontend ContaFlow usa React + Vite + TypeScript strict, sem Next.js (App Router). Stack: React 18, react-router-dom v6, @tanstack/react-query v5, react-hook-form + zod, axios, Tailwind CSS, lucide-react, react-hot-toast.

**Why:** Projeto iniciado antes da migração para Next.js. O roteamento e feito via BrowserRouter.

**How to apply:** Nao usar diretivas `'use client'` ou `'use server'` — elas nao tem efeito aqui (o projeto nao e Next.js). Server Components nao existem. Todo componente e client-side. A diretiva `'use client'` e aceita pelo TS mas ignorada pelo Vite.

Componentes UI proprios em `frontend/src/components/ui/`:
- Button, Input, Card, Badge, Select, Dialog, FormField, StateViews

Hook principal: `frontend/src/lib/hooks/useOperations.ts`
- Exporta todos os tipos (AccountingClient, DeadlineItem, etc.)
- Exporta queries: useClients, useDeadlines, useDocuments, useCertificates, useReceivables, useDashboardOverview
- Exporta mutations: useCreateClient, useCreateDeadline, useCreateDocument, useCreateCertificate, useCreateReceivable, useUpdateReceivable
- Exporta deletes: useDeleteClient, useDeleteDeadline, useDeleteDocument, useDeleteCertificate, useDeleteReceivable
- Exporta helpers: moneyBRL, dateBR

API base: axios instance em `frontend/src/lib/api.ts` — injeta Bearer token e X-Tenant-ID de localStorage.

**Deploy:** Frontend em producao na Vercel desde 2026-05-20.
- URL canonica: https://contaflow-frontend.vercel.app
- Projeto Vercel: v-stack-solution/contaflow-frontend
- Env var de producao: VITE_API_URL=https://contaflow.fly.dev
- vercel.json com rewrite SPA: `{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }`
- Build command: `npm run build` (tsc && vite build) — sem erros, apenas warning de chunk size (955 kB JS)
