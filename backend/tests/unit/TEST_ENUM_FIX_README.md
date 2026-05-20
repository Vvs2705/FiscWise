# Testes do Enum Fix (fix_enums_startup.py)

## Visão Geral

Suite completa de testes para o fix de PostgreSQL enum case mismatch.

**Arquivo:** `backend/tests/unit/test_enum_fix.py`

**Total:** 35+ testes cobrindo:
- Normalização de DSN (postgres:// → postgresql://, ssl → sslmode)
- Detecção de tabelas
- Detecção de enum UPPERCASE
- Execução de DDL com tratamento de erros
- Orquestração completa (fix_enums)
- Casos edge (primeira deploy, DATABASE_URL vazio)

## Estrutura dos Testes

### 1. TestBuildDsn (7 testes)
```python
# postgres:// → postgresql://
# asyncpg style ?ssl=require → libpq style ?sslmode=require
# Preservação de query strings complexas
```

**Cobertura:**
- Scheme normalization
- SSL parameter conversion
- Query string preservation
- Combined transformations

### 2. TestExec (6 testes)
```python
# Sucesso
# Benign errors: "already exists", "does not exist", "undefined column"
# Fatal errors: connection refused, syntax error, etc.
```

**Cobertura:**
- Padrões de erro benignos
- Erros fatais
- Logging apropriado

### 3. TestCheckTables (5 testes)
```python
# Ambas tabelas existem
# Apenas users existe
# Apenas tenants existe
# Nenhuma existe (first deploy)
# Query information_schema correta
```

**Cobertura:**
- Detecção de existência correta
- SQL query validação

### 4. TestEnumHasUppercase (5 testes)
```python
# Detecção de UPPERCASE
# All lowercase → False
# Non-existent enum → False
# Uso correto de pg_enum system tables
```

**Cobertura:**
- Lógica de detecção
- Casos edge (enum inexistente)
- Query system tables

### 5. TestFixEnums (6 testes)
```python
# psycopg não instalado
# No-op: tabelas ausentes (first deploy)
# No-op: enums já lowercase
# Falha de conexão
# Fix user_role_enum
# Fix subscription_status_enum
```

**Cobertura:**
- Orquestração completa
- Ambos os enums
- Error handling
- Graceful degradation

### 6. TestFixEnumsCLI (2 testes)
```python
# DATABASE_URL vazio
# DATABASE_URL env var respeitado
```

### 7. TestFixEnumsIntegration (2 testes)
```python
# Workflow completo: ambos enums precisam fix
# Transformação DSN na conexão
```

## Rodando os Testes

### Ambiente

O projeto ContaFlow usa pytest. Instale a dependência:

```bash
pip install pytest
```

### Executar Todos os Testes

```bash
# From backend directory
cd backend

# Todos os testes enum_fix
pytest tests/unit/test_enum_fix.py -v

# Apenas TestBuildDsn
pytest tests/unit/test_enum_fix.py::TestBuildDsn -v

# Apenas um teste específico
pytest tests/unit/test_enum_fix.py::TestBuildDsn::test_postgres_scheme_to_postgresql -v
```

### Com Cobertura

```bash
# Gera report de cobertura
pytest tests/unit/test_enum_fix.py \
  --cov=fix_enums_startup \
  --cov-report=term-missing \
  --cov-report=html

# Abre report: htmlcov/index.html
```

### Debug

```bash
# Mostra print statements e logs
pytest tests/unit/test_enum_fix.py -v -s

# Para em erro
pytest tests/unit/test_enum_fix.py -v --pdb

# Detalhes de fixture
pytest tests/unit/test_enum_fix.py --fixtures
```

## Dependências de Mock

Todos os testes usam **mocks** — nenhum banco de dados real é necessário.

```python
# Exemplo de fixture mock
@pytest.fixture
def mock_psycopg_connection():
    """Mock psycopg connection"""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = Mock()
    conn.cursor.return_value.__exit__ = Mock()
    return conn
```

## Validação Manual

Para validação rápida sem pytest:

```bash
# Testar normalização DSN
cd backend && python << 'EOF'
import sys
sys.path.insert(0, '.')
from fix_enums_startup import _build_dsn
from urllib.parse import urlparse, parse_qs

url = "postgres://user:pass@localhost/db?ssl=require"
dsn = _build_dsn(url)
params = parse_qs(urlparse(dsn).query)
assert params.get("sslmode") == ["require"]
assert "ssl" not in params
print("[OK] DSN normalization works")
EOF
```

## Coverage Report Esperado

Ao rodar com `--cov`, você deve ver:

```
fix_enums_startup.py
  _build_dsn         100%
  _check_tables      100%
  _enum_has_uppercase 100%
  _exec              100%
  fix_enums          90%+ (algumas branches são hard-path com psycopg real)
```

> Nota: 100% coverage em funções puras; `fix_enums` pode ter branches não-alcançáveis nos testes (e.g., psycopg import error, real DB connection failures).

## Casos de Uso

### Seu PR toca fix_enums_startup.py?

```bash
# Rode todos os testes
pytest tests/unit/test_enum_fix.py -v --cov=fix_enums_startup
```

### Novo enum ou mudança na logica de detecção?

1. Atualize `_enum_has_uppercase()` em fix_enums_startup.py
2. Adicione teste em `TestEnumHasUppercase`
3. Rode `pytest tests/unit/test_enum_fix.py::TestEnumHasUppercase -v`

### Novo padrão de erro benígno?

1. Adicione pattern em `_BENIGN_ERROR_PATTERNS`
2. Adicione teste em `TestExec` com o novo padrão
3. Rode `pytest tests/unit/test_enum_fix.py::TestExec -v`

## Troubleshooting

### "ModuleNotFoundError: No module named 'psycopg'"

Esperado — os testes mockam psycopg. A função `fix_enums()` só chama `import psycopg` dentro de um try/except.

### "ImportError: No module named 'fastapi'"

Se rodar com `conftest.py` global, isso é esperado. Use o `conftest.py` em `tests/unit/`:

```bash
# Não faça isso (carrega conftest.py do projeto inteiro)
pytest tests/unit/test_enum_fix.py

# Faça isso (se tiver problemas)
cd backend/tests/unit && pytest test_enum_fix.py -v
```

### Testes passam mas eu quer validar contra banco real?

O arquivo `fix_enums_startup.py` é auto-contido e pode rodar manually:

```bash
# Com DATABASE_URL real (Supabase, PostgreSQL, etc.)
DATABASE_URL="postgresql://user:pass@host/db" python backend/fix_enums_startup.py
```

## Próximos Passos

### Adicionar testes de comportamento de run_migrations.py

Se `run_migrations.py` chamar `fix_enums()`, adicionar testes de integração em:
```
backend/tests/integration/test_migrations.py
```

### Cobertura de Alembic migrations

Se usar Alembic, adicionar tests que verifiquem:
1. Enum é criado com values lowercase em novas migrations
2. fix_enums() não precisa rodar em novos deploys (idempotent)

## Referências

- **Arquivo testado:** `backend/fix_enums_startup.py`
- **Arquivo de testes:** `backend/tests/unit/test_enum_fix.py`
- **Fixtures:** Mock de psycopg3, sem DB real necessária
- **Stack:** pytest + unittest.mock
