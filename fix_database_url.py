#!/usr/bin/env python3
"""
Fix DATABASE_URL for asyncpg compatibility.

asyncpg doesn't recognize sslmode parameter.
Solution: Replace it with ssl parameter and add statement_cache_size.

Problem URL: postgresql+asyncpg://user:pass@host:5432/db?sslmode=require
Fixed URL:   postgresql+asyncpg://user:pass@host:5432/db?ssl=require&statement_cache_size=0
"""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import sys

def fix_database_url(url):
    """Remove sslmode and add asyncpg-compatible parameters."""
    parsed = urlparse(url)

    # Parse query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove sslmode if present (asyncpg doesn't support it)
    if 'sslmode' in params:
        print(f"Found sslmode={params['sslmode']}, removing...")
        del params['sslmode']

    # Add asyncpg-compatible SSL parameter
    params['ssl'] = ['require']

    # Add statement cache size (prevents issues with prepared statements)
    params['statement_cache_size'] = ['0']

    # Rebuild query string
    new_query = urlencode(params, doseq=True)

    # Rebuild URL
    fixed_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return fixed_url


if __name__ == '__main__':
    # Example: postgresql+asyncpg://postgres:pw@host:5432/postgres?sslmode=require
    test_url = "postgresql+asyncpg://postgres:abc123@postgres.lkgmgbieottygodrdubi.supabase.co:5432/postgres?sslmode=require"

    fixed = fix_database_url(test_url)
    print(f"\nOriginal: {test_url}")
    print(f"Fixed:    {fixed}")
    print("\nUse this fixed URL in Fly.io:")
    print(f"  flyctl secrets set DATABASE_URL='{fixed}'")
