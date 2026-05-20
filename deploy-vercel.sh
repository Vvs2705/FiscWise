#!/bin/bash
# ContaFlow Frontend - Deploy to Vercel
# Prerequisites: vercel CLI installed (npm install -g vercel)

set -e

echo "🚀 Deploying ContaFlow Frontend to Vercel..."
echo ""

# Ensure we're in frontend directory
cd "$(dirname "$0")/frontend" || exit 1

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Set production environment variables
echo "⚙️  Setting production environment variables..."
export VITE_API_URL=https://contaflow.fly.dev

# Build frontend if not already built
if [ ! -d "dist" ]; then
    echo "📦 Building frontend..."
    npm run build
else
    echo "✅ Build directory found, skipping build step"
fi

# Deploy to Vercel
echo "📤 Deploying to Vercel (production)..."
vercel --prod --yes --env VITE_API_URL=https://contaflow.fly.dev

echo ""
echo "✅ Deployment complete!"
echo "Frontend is now live at your Vercel URL"
echo ""
echo "🔗 Next steps:"
echo "  1. Test the frontend by visiting the Vercel URL"
echo "  2. Register a new user"
echo "  3. Verify that the dashboard loads with data from https://contaflow.fly.dev"
