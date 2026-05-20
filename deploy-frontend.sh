#!/bin/bash
# ContaFlow Frontend - Deploy to Vercel

set -e

echo "🚀 ContaFlow Frontend Deployment to Vercel"
echo "=========================================="
echo ""

# Ensure we're in frontend directory
cd "$(dirname "$0")/frontend" || exit 1

# Check if Node/npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js"
    exit 1
fi

# Check if Vercel CLI is installed, install if needed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Set environment for production build
echo "⚙️  Setting up production configuration..."
export VITE_API_URL=https://contaflow.fly.dev

# Verify build is production-ready
if [ ! -d "dist" ]; then
    echo "📦 Building frontend for production..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "❌ Frontend build failed"
        exit 1
    fi
    echo "✅ Frontend build successful"
else
    echo "✅ Build directory found, skipping rebuild"
fi

# Deploy to Vercel (production)
echo ""
echo "📤 Deploying to Vercel (production)..."
echo "   Using API URL: $VITE_API_URL"
echo ""

vercel --prod --yes --env VITE_API_URL=https://contaflow.fly.dev

echo ""
echo "=========================================="
echo "✅ Frontend deployed successfully!"
echo ""
echo "📋 Next Steps:"
echo "   1. Visit the Vercel deployment URL"
echo "   2. Register a new user account"
echo "   3. Verify dashboard loads data from API"
echo "   4. Test tenant isolation (logout & register another user)"
echo ""
