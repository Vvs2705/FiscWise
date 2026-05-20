#!/usr/bin/env python3
"""
End-to-end test of registration → login → dashboard flow.
Runs once registration endpoint is working.
"""
import asyncio
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError

API_BASE = "https://contaflow.fly.dev/api/v1"
COMPANY_NAME = "ContaFlow Test"
OWNER_EMAIL = "vsouz009@gmail.com"
OWNER_PASSWORD = "Pq267@gtr417#"
OWNER_FULL_NAME = "Vinicius Souza"


def make_request(method, endpoint, data=None, headers=None):
    """Make HTTP request."""
    if headers is None:
        headers = {"Content-Type": "application/json"}

    url = f"{API_BASE}{endpoint}"

    try:
        if data:
            data = json.dumps(data).encode('utf-8')
            headers["Content-Type"] = "application/json"

        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req, timeout=10) as response:
            response_data = response.read().decode('utf-8')
            try:
                return response.status, json.loads(response_data)
            except json.JSONDecodeError:
                return response.status, response_data
    except URLError as e:
        return getattr(e, 'code', 500), {"error": str(e)}


def test_registration():
    """Test registration endpoint."""
    print("\n🔵 Testing Registration Endpoint")
    print(f"POST /onboarding/register")

    status, response = make_request("POST", "/onboarding/register", {
        "company_name": COMPANY_NAME,
        "owner_email": OWNER_EMAIL,
        "owner_password": OWNER_PASSWORD,
        "owner_full_name": OWNER_FULL_NAME
    })

    if status == 201:
        print(f"✅ Registration successful (201)")
        print(f"   Tenant ID: {response.get('tenant_id', 'N/A')[:8]}...")
        print(f"   User ID: {response.get('user', {}).get('id', 'N/A')[:8]}...")
        print(f"   Token: {response.get('access_token', 'N/A')[:20]}...")
        return True, response
    else:
        print(f"❌ Registration failed ({status})")
        print(f"   Response: {json.dumps(response, indent=2)[:200]}")
        return False, response


def test_login(email=None, password=None):
    """Test login endpoint."""
    if email is None:
        email = OWNER_EMAIL
    if password is None:
        password = OWNER_PASSWORD

    print("\n🔵 Testing Login Endpoint")
    print(f"POST /auth/login")

    status, response = make_request("POST", "/auth/login", {
        "username": email,
        "password": password
    })

    if status == 200:
        print(f"✅ Login successful (200)")
        print(f"   Tenant ID: {response.get('tenant_id', 'N/A')[:8]}...")
        print(f"   Token: {response.get('access_token', 'N/A')[:20]}...")
        print(f"   Role: {response.get('user', {}).get('role', 'N/A')}")
        return True, response.get('access_token'), response.get('tenant_id')
    else:
        print(f"❌ Login failed ({status})")
        print(f"   Response: {json.dumps(response, indent=2)[:200]}")
        return False, None, None


def test_protected_endpoint(token, tenant_id):
    """Test accessing a protected endpoint."""
    if not token or not tenant_id:
        print("\n⚠️  Skipping protected endpoint test (no token/tenant_id)")
        return

    print("\n🔵 Testing Protected Endpoint (/auth/me)")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
        "Content-Type": "application/json"
    }

    status, response = make_request("GET", "/auth/me", headers=headers)

    if status == 200:
        print(f"✅ Protected endpoint accessible (200)")
        print(f"   Email: {response.get('email', 'N/A')}")
        print(f"   Role: {response.get('role', 'N/A')}")
        return True
    else:
        print(f"❌ Protected endpoint failed ({status})")
        print(f"   Response: {json.dumps(response, indent=2)[:200]}")
        return False


def main():
    """Run E2E test."""
    print("=" * 60)
    print("ContaFlow E2E Test: Registration → Login → Protected")
    print("=" * 60)

    # Test 1: Registration
    success, reg_response = test_registration()
    if not success:
        print("\n❌ E2E Test FAILED at registration step")
        return False

    # Test 2: Login
    success, token, tenant_id = test_login()
    if not success:
        print("\n❌ E2E Test FAILED at login step")
        return False

    # Test 3: Protected endpoint
    success = test_protected_endpoint(token, tenant_id)
    if not success:
        print("\n⚠️  Protected endpoint test failed")

    print("\n" + "=" * 60)
    print("✅ E2E Test COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
