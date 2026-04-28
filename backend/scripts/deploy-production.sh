#!/bin/bash

# Production deployment script for ContaFlow
# This script runs database migrations and starts the application

set -e  # Exit on error

echo "🚀 Starting ContaFlow production deployment..."

# Run database migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Verify migrations
echo "✅ Verifying migrations..."
alembic current

# Check if pgvector extension is enabled
echo "🔍 Checking pgvector extension..."
python -c "
import asyncio
from sqlalchemy import text
from app.core.deps import AsyncSessionLocal

async def check_pgvector():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(\"SELECT * FROM pg_extension WHERE extname = 'vector'\"))
        if result.fetchone():
            print('✅ pgvector extension is enabled')
        else:
            print('⚠️  pgvector extension not found - attempting to enable...')
            await session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            await session.commit()
            print('✅ pgvector extension enabled')

asyncio.run(check_pgvector())
"

# Start application
echo "🎉 Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}
