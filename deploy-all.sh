#!/bin/bash
set -e

echo "🚀 ContaFlow Complete Production Deployment"
echo "==========================================="
echo ""

# Test 1: API Health
echo "1️⃣  Testing API health..."
if ! curl -s https://contaflow.fly.dev/api/v1/health | grep -q "healthy"; then
    echo "   ❌ API health check failed"
    exit 1
fi
echo "   ✅ API is healthy"

# Test 2: User Registration  
echo ""
echo "2️⃣  Testing user registration (database connectivity)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST https://contaflow.fly.dev/api/v1/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "E2E Test Company",
    "owner_email": "e2e@test.com",
    "owner_password": "E2ETest123!",
    "owner_full_name": "E2E Tester"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" -ne 201 ]; then
    echo "   ❌ Registration failed with HTTP $HTTP_CODE"
    echo "   Response: $BODY"
    exit 1
fi
echo "   ✅ User registration successful (HTTP 201)"
JWT_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 | head -1)
if [ -n "$JWT_TOKEN" ]; then
    echo "   🔑 JWT token obtained: ${JWT_TOKEN:0:20}..."
fi

# Test 3: Deploy Frontend
echo ""
echo "3️⃣  Deploying frontend to Vercel..."
cd "$(dirname "$0")/frontend" || exit 1

if ! command -v vercel &> /dev/null; then
    echo "   📦 Installing Vercel CLI..."
    npm install -g vercel
fi

export VITE_API_URL=https://contaflow.fly.dev
echo "   ⚙️  Vercel deploy with API: $VITE_API_URL"

if vercel --prod --yes --env VITE_API_URL=https://contaflow.fly.dev; then
    echo "   ✅ Frontend deployment successful"
else
    echo "   ❌ Frontend deployment failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "✅ COMPLETE: Phase 3-0 Production Deployment"
echo ""
echo "📋 What's now live:"
echo "   • API: https://contaflow.fly.dev/api/v1"
echo "   • Frontend: Deployed to Vercel (check your project)"
echo "   • Database: PostgreSQL via Supabase"
echo "   • User system: Fully operational"
echo ""
echo "🧪 Next steps:"
echo "   1. Visit your Vercel frontend URL"
echo "   2. Register a new account"
echo "   3. Login with credentials"
echo "   4. Verify dashboard loads data from API"
echo ""
