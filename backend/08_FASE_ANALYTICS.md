# FASE 8 - Analytics & Metrics Dashboard

## 🎯 Objetivo

Implementar sistema completo de analytics e métricas para o ContaFlow, fornecendo insights sobre:
- Uso de tokens por tenant (billing)
- Estatísticas de sessões de chat
- Métricas de documentos e chunks
- Performance de RAG (Retrieval-Augmented Generation)
- Dashboard data agregada

## 📋 Escopo

### 1. **Analytics Models** (`app/models/analytics.py`)

Criar modelos para agregação de métricas:

#### DailyUsageMetrics
- `id`: UUID PK
- `tenant_id`: UUID FK (TenantBase)
- `date`: Date (índice único composto com tenant_id)
- `total_sessions`: Integer - Sessões criadas no dia
- `total_messages`: Integer - Mensagens enviadas no dia
- `total_input_tokens`: Integer - Tokens de entrada consumidos
- `total_output_tokens`: Integer - Tokens de saída gerados
- `total_documents`: Integer - Documentos ingeridos no dia
- `total_chunks`: Integer - Chunks criados no dia
- `created_at`, `updated_at`: Timestamps

### 2. **Analytics Service** (`app/services/analytics_service.py`)

Implementar serviço de agregação de métricas:

**Métodos:**
- `get_token_usage_summary(tenant_id, start_date, end_date)` → Dict
  - Total input/output tokens
  - Custo estimado (baseado em pricing do Claude)
  - Breakdown por modelo
  - Breakdown por endpoint

- `get_session_analytics(tenant_id, start_date, end_date)` → Dict
  - Total de sessões
  - Total de mensagens
  - Média de mensagens por sessão
  - Sessões mais ativas

- `get_document_analytics(tenant_id)` → Dict
  - Total de documentos
  - Total de chunks
  - Média de chunks por documento
  - Documentos por status

- `get_daily_metrics(tenant_id, days=30)` → List[DailyUsageMetrics]
  - Métricas diárias dos últimos N dias
  - Preparado para gráficos de linha

- `aggregate_daily_metrics(tenant_id, date)` → DailyUsageMetrics
  - Agrega métricas de um dia específico
  - Upsert (insert or update)

### 3. **Analytics Schemas** (`app/schemas/analytics.py`)

Criar schemas Pydantic para responses:

- `TokenUsageSummary` - Resumo de uso de tokens
- `SessionAnalytics` - Estatísticas de sessões
- `DocumentAnalytics` - Estatísticas de documentos
- `DailyMetricsResponse` - Métricas diárias
- `DashboardData` - Dados agregados para dashboard

### 4. **Analytics API Endpoints** (`app/api/v1/endpoints/analytics.py`)

Implementar endpoints REST:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/analytics/token-usage` | Resumo de uso de tokens |
| GET | `/api/v1/analytics/sessions` | Estatísticas de sessões |
| GET | `/api/v1/analytics/documents` | Estatísticas de documentos |
| GET | `/api/v1/analytics/daily-metrics` | Métricas diárias (últimos 30 dias) |
| GET | `/api/v1/analytics/dashboard` | Dados agregados para dashboard |

**Query Parameters:**
- `start_date`: Optional[date] - Data inicial (default: 30 dias atrás)
- `end_date`: Optional[date] - Data final (default: hoje)
- `days`: Optional[int] - Número de dias (default: 30)

### 5. **Background Task** (Opcional - Fase 8.5)

Criar task Celery para agregação diária automática:

```python
@celery_app.task
def aggregate_daily_metrics_task():
    """Agrega métricas de todos os tenants para o dia anterior"""
    yesterday = date.today() - timedelta(days=1)
    # Para cada tenant ativo:
    #   - Agregar métricas do dia
    #   - Salvar em DailyUsageMetrics
```

## 🔧 Implementação Técnica

### SQL Queries Otimizadas

#### Token Usage Summary
```sql
SELECT 
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    model,
    endpoint
FROM token_usage_logs
WHERE tenant_id = :tenant_id
  AND created_at BETWEEN :start_date AND :end_date
GROUP BY model, endpoint
```

#### Session Analytics
```sql
SELECT 
    COUNT(DISTINCT cs.id) as total_sessions,
    COUNT(cm.id) as total_messages,
    AVG(cs.message_count) as avg_messages_per_session
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cm.session_id = cs.id
WHERE cs.tenant_id = :tenant_id
  AND cs.created_at BETWEEN :start_date AND :end_date
```

#### Document Analytics
```sql
SELECT 
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(dc.id) as total_chunks,
    AVG(chunk_count) as avg_chunks_per_doc,
    d.status,
    COUNT(*) as count
FROM documents d
LEFT JOIN document_chunks dc ON dc.document_id = d.id
WHERE d.tenant_id = :tenant_id
GROUP BY d.status
```

### Pricing Calculation (Claude)

```python
# Claude 3.5 Haiku pricing (exemplo)
PRICING = {
    "claude-3-5-haiku-20241022": {
        "input": 0.00025,   # $0.25 per 1M tokens
        "output": 0.00125   # $1.25 per 1M tokens
    }
}

def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    pricing = PRICING.get(model, {"input": 0, "output": 0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
```

## 📊 Dashboard Data Structure

```json
{
  "token_usage": {
    "total_input_tokens": 150000,
    "total_output_tokens": 75000,
    "total_cost_usd": 0.13125,
    "by_model": {
      "claude-3-5-haiku-20241022": {
        "input_tokens": 150000,
        "output_tokens": 75000,
        "cost_usd": 0.13125
      }
    },
    "by_endpoint": {
      "chat": {
        "input_tokens": 150000,
        "output_tokens": 75000
      }
    }
  },
  "sessions": {
    "total_sessions": 45,
    "total_messages": 320,
    "avg_messages_per_session": 7.1
  },
  "documents": {
    "total_documents": 12,
    "total_chunks": 487,
    "avg_chunks_per_document": 40.6,
    "by_status": {
      "completed": 10,
      "processing": 1,
      "failed": 1
    }
  },
  "daily_metrics": [
    {
      "date": "2026-04-27",
      "total_sessions": 5,
      "total_messages": 38,
      "total_input_tokens": 12000,
      "total_output_tokens": 6000
    }
    // ... últimos 30 dias
  ]
}
```

## 🔐 Segurança

- ✅ Todos os endpoints requerem autenticação (`get_current_user`)
- ✅ Todos os endpoints requerem `X-Tenant-ID` header
- ✅ Isolamento multi-tenant via `current_user.tenant_id`
- ✅ Apenas dados do próprio tenant são retornados

## 🧪 Testes

### Unit Tests (`tests/test_analytics.py`)

```python
async def test_get_token_usage_summary(db_session, test_tenant):
    # Criar logs de uso
    # Chamar analytics_service.get_token_usage_summary()
    # Verificar totais e breakdown

async def test_get_session_analytics(db_session, test_tenant):
    # Criar sessões e mensagens
    # Chamar analytics_service.get_session_analytics()
    # Verificar contadores e médias

async def test_aggregate_daily_metrics(db_session, test_tenant):
    # Criar dados de um dia
    # Chamar analytics_service.aggregate_daily_metrics()
    # Verificar DailyUsageMetrics criado
```

### Integration Tests

```bash
# Criar tenant de teste
# Criar sessões, mensagens, documentos
# Chamar endpoints de analytics
# Verificar responses
```

## 📈 Métricas de Performance

- Query de token usage: < 100ms
- Query de session analytics: < 150ms
- Query de document analytics: < 100ms
- Query de daily metrics (30 dias): < 200ms
- Dashboard completo: < 500ms

**Otimizações:**
- Índices em `token_usage_logs.created_at`
- Índices em `chat_sessions.created_at`
- Índices em `documents.created_at`
- Agregação diária pré-calculada (DailyUsageMetrics)

## 🚀 Entregáveis

### Arquivos a Criar

1. `app/models/analytics.py` - DailyUsageMetrics model
2. `app/services/analytics_service.py` - AnalyticsService class
3. `app/schemas/analytics.py` - Pydantic schemas
4. `app/api/v1/endpoints/analytics.py` - 5 endpoints REST
5. `alembic/versions/xxx_add_analytics_tables.py` - Migration

### Arquivos a Modificar

1. `app/models/__init__.py` - Exportar DailyUsageMetrics
2. `app/api/v1/api.py` - Registrar analytics router

### Documentação

1. `FASE_8_SUMMARY.md` - Resumo da implementação

## ✅ Critérios de Aceitação

- [ ] DailyUsageMetrics model criado e registrado
- [ ] AnalyticsService implementado com 5 métodos
- [ ] 5 endpoints REST implementados e autenticados
- [ ] Schemas Pydantic criados
- [ ] Migration gerada e aplicada
- [ ] Testes unitários passando
- [ ] Endpoints documentados no Swagger
- [ ] Performance < 500ms para dashboard completo
- [ ] Isolamento multi-tenant validado

## 🎯 Próximos Passos (Fase 9)

Após conclusão da Fase 8:
- **Fase 9**: Frontend React + Dashboard UI
- **Fase 10**: Deployment & CI/CD

---

**Fase 8 - Analytics: PRONTO PARA IMPLEMENTAÇÃO** 📊📈🚀
