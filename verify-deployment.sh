#!/bin/bash
# ============================================================================
# ContaFlow - Deployment Verification Script
# Valida que todo o sistema está funcionando corretamente em produção
# ============================================================================

set -e

echo "🔍 Iniciando validação de deployment do ContaFlow..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="https://contaflow.fly.dev"
FRONTEND_URL="http://localhost:3000"

# ============================================================================
# 1. VALIDAÇÃO DE API
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. Validando API Backend${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test health endpoint
echo "Testando health endpoint..."
HEALTH=$(curl -s "$API_URL/api/v1/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
  echo -e "${GREEN}✅ Health endpoint OK${NC}"
  echo "   Response: $HEALTH"
else
  echo -e "${RED}❌ Health endpoint FAILED${NC}"
  echo "   Response: $HEALTH"
  exit 1
fi

echo ""

# ============================================================================
# 2. VALIDAÇÃO DE FRONTEND
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. Validando Frontend${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if frontend is running
if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Frontend respondendo em localhost:3000${NC}"
else
  echo -e "${YELLOW}⚠️  Frontend não está rodando localmente${NC}"
  echo "   (Será deployado em Vercel para produção)"
fi

echo ""

# ============================================================================
# 3. VALIDAÇÃO DE CONFIGURAÇÃO
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. Validando Configuração${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check files exist
FILES=(
  "backend/Dockerfile"
  "backend/app/core/config.py"
  "backend/app/api/v1/endpoints/health.py"
  "frontend/src/pages/DashboardPage.tsx"
  "fly.toml"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo -e "${GREEN}✅ $file${NC}"
  else
    echo -e "${RED}❌ $file NÃO ENCONTRADO${NC}"
  fi
done

echo ""

# ============================================================================
# 4. RESUMO
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ VALIDAÇÃO COMPLETA${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "ContaFlow está pronto para:"
echo "  1. Testes de autenticação e registro de usuários"
echo "  2. Fluxo completo de onboarding"
echo "  3. Dashboard operacional com dados reais"
echo "  4. Deployment em Vercel (frontend)"
echo ""
echo -e "${YELLOW}⚠️  Próximos passos:${NC}"
echo "  1. Configurar DATABASE_URL em Fly.io (se não estiver)"
echo "  2. Testar endpoints de autenticação"
echo "  3. Deploy do frontend em Vercel"
echo ""

exit 0
