#!/bin/bash
# Test ContaFlow API connectivity after Fly.io deployment

API_URL="https://contaflow.fly.dev"

echo "🧪 Testing ContaFlow API Endpoints"
echo "=================================="
echo ""

# Test 1: Health Check (no database required)
echo "1️⃣  Testing Health Check (no DB required)..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/api/v1/health")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -1)

if [ "$HEALTH_CODE" -eq 200 ]; then
    echo "   ✅ Health Check: HTTP $HEALTH_CODE OK"
    echo "   Response: $HEALTH_BODY"
else
    echo "   ❌ Health Check: HTTP $HEALTH_CODE FAILED"
    echo "   Response: $HEALTH_BODY"
    exit 1
fi

echo ""

# Test 2: User Registration (requires database connectivity)
echo "2️⃣  Testing User Registration (with DB)..."
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/onboarding/register" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "owner_email": "test@example.com",
    "owner_password": "TestPass123!"
  }')

REGISTER_CODE=$(echo "$REGISTER_RESPONSE" | tail -1)
REGISTER_BODY=$(echo "$REGISTER_RESPONSE" | head -1)

if [ "$REGISTER_CODE" -eq 201 ]; then
    echo "   ✅ User Registration: HTTP $REGISTER_CODE CREATED"
    echo "   Response: $REGISTER_BODY"
    # Extract JWT token if present
    TOKEN=$(echo "$REGISTER_BODY" | grep -o '"access_token":"[^"]*' | head -1 | cut -d'"' -f4)
    if [ -n "$TOKEN" ]; then
        echo "   🔑 JWT Token obtained: ${TOKEN:0:20}..."
    fi
else
    echo "   ❌ User Registration: HTTP $REGISTER_CODE FAILED"
    echo "   Response: $REGISTER_BODY"
    echo "   (Expected 201 Created)"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ All API tests passed!"
echo "Database connectivity: CONFIRMED"
echo ""
