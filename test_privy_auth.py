#!/usr/bin/env python3
"""
Test script for Privy authentication and account linking
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

print("=" * 80)
print("PRIVY AUTHENTICATION TEST")
print("=" * 80)

# Test 1: Health check
print("\n[1/5] Testing health endpoint...")
response = requests.get(f"{BASE_URL}/api/health")
if response.status_code == 200:
    print("✓ Health check passed")
    print(f"  Response: {response.json()}")
else:
    print(f"✗ Health check failed: {response.status_code}")
    exit(1)

# Test 2: Try to access agents without auth (should fail)
print("\n[2/5] Testing unauthenticated agent access (should fail)...")
response = requests.get(f"{BASE_URL}/api/agents")
if response.status_code == 401:
    print("✓ Correctly rejected unauthenticated request")
    print(f"  Response: {response.json()}")
else:
    print(f"✗ Should have returned 401, got: {response.status_code}")
    print(f"  Response: {response.json()}")

# Test 3: Try to create agent without auth (should fail)
print("\n[3/5] Testing unauthenticated agent creation (should fail)...")
agent_data = {
    "url": "https://test-agent.com",
    "bot_token": "test:token123",
    "price": 0.005
}
response = requests.post(f"{BASE_URL}/api/agents", json=agent_data)
if response.status_code == 401:
    print("✓ Correctly rejected unauthenticated request")
    print(f"  Response: {response.json()}")
else:
    print(f"✗ Should have returned 401, got: {response.status_code}")
    print(f"  Response: {response.json()}")

# Test 4: Test link completion without auth (should fail)
print("\n[4/5] Testing unauthenticated link completion (should fail)...")
link_data = {"code": "test-code-123"}
response = requests.post(f"{BASE_URL}/api/link/complete", json=link_data)
if response.status_code == 401:
    print("✓ Correctly rejected unauthenticated request")
    print(f"  Response: {response.json()}")
else:
    print(f"✗ Should have returned 401, got: {response.status_code}")
    print(f"  Response: {response.json()}")

# Test 5: Test pending link creation via database
print("\n[5/5] Testing pending link database structure...")
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)
    
    # Check pending_links table
    try:
        result = supabase.table("pending_links").select("*").limit(1).execute()
        print("✓ Pending links table accessible")
        if result.data:
            print(f"  Sample record columns: {list(result.data[0].keys())}")
    except Exception as e:
        print(f"✗ Error accessing pending_links: {e}")
    
    # Check linked_accounts table
    try:
        result = supabase.table("linked_accounts").select("*").limit(1).execute()
        print("✓ Linked accounts table accessible")
        if result.data:
            print(f"  Sample record columns: {list(result.data[0].keys())}")
        else:
            print("  Table is empty (expected for new setup)")
    except Exception as e:
        print(f"✗ Error accessing linked_accounts: {e}")
    
    # Check agents table with user_id
    try:
        result = supabase.table("agents").select("*").limit(1).execute()
        print("✓ Agents table accessible")
        if result.data:
            columns = list(result.data[0].keys())
            print(f"  Columns: {columns}")
            if "user_id" in columns:
                print("  ✓ user_id column exists")
            else:
                print("  ✗ user_id column missing!")
    except Exception as e:
        print(f"✗ Error accessing agents: {e}")

print("\n" + "=" * 80)
print("AUTHENTICATION TEST COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("1. Open the frontend in a browser")
print("2. You should be prompted to 'Continue with Google'")
print("3. After authentication, you should be able to create agents")
print("4. Test the /link?code=XXX flow by accessing it directly")
print("\nFrontend URL: http://localhost:3000")
print("=" * 80)
