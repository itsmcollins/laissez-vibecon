#!/usr/bin/env python3
"""
Test individual payment flow components
Tests each part of the payment flow in isolation
"""

import asyncio
import httpx
from supabase import create_client
from privy import PrivyAPI
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
PRIVY_APP_ID = os.environ.get("PRIVY_APP_ID")
PRIVY_APP_SECRET = os.environ.get("PRIVY_APP_SECRET")
BOT_TOKEN = "7305057804:AAFe6qQVvVVPOCsD_rWn1wMOaQIenBpXSS0"
USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
USDC_DECIMALS = 6

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
privy_client = PrivyAPI(app_id=PRIVY_APP_ID, app_secret=PRIVY_APP_SECRET)


def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


async def check_usdc_balance(wallet_address: str):
    """Check USDC balance for a wallet"""
    try:
        async with httpx.AsyncClient() as client:
            rpc_url = "https://sepolia.base.org"
            address_padded = wallet_address[2:].lower().zfill(64)
            data = f"0x70a08231{address_padded}"
            
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    balance_hex = result["result"]
                    balance_atomic = int(balance_hex, 16)
                    balance_usdc = balance_atomic / (10 ** USDC_DECIMALS)
                    return balance_usdc
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
    return None


async def test_agent_configuration():
    """Test 1: Check if agent is configured correctly"""
    print_header("TEST 1: Agent Configuration")
    
    agent = supabase.table("agents").select("*").eq("bot_token", BOT_TOKEN).execute()
    
    if agent.data:
        agent_data = agent.data[0]
        print(f"✅ Agent Found:")
        print(f"   Name: {agent_data.get('name')}")
        print(f"   URL: {agent_data.get('url')}")
        print(f"   Price: ${agent_data.get('price')}")
        print(f"   Creator: {agent_data.get('user_id')[:30]}...")
        return agent_data
    else:
        print("❌ Agent not found")
        return None


async def test_creator_wallet(user_id):
    """Test 2: Check if creator has wallet and balance"""
    print_header("TEST 2: Creator Wallet & Balance")
    
    print(f"Checking wallet for user: {user_id[:30]}...")
    
    try:
        user_data = privy_client.users.get(user_id)
        
        wallet_account = None
        for account in user_data.linked_accounts:
            if account.type == "wallet" and hasattr(account, 'chain_type'):
                if account.chain_type == "ethereum" and hasattr(account, 'address'):
                    wallet_account = account
                    break
        
        if wallet_account:
            address = wallet_account.address
            delegated = getattr(wallet_account, 'delegated', False)
            
            print(f"✅ Creator Wallet Found:")
            print(f"   Address: {address}")
            print(f"   Delegated: {delegated}")
            
            balance = await check_usdc_balance(address)
            if balance is not None:
                print(f"   Balance: {balance:.6f} USDC")
                if balance >= 0.001:
                    print(f"   💰 Sufficient to receive payments")
                else:
                    print(f"   ⚠️  Low balance (but can still receive)")
            
            return address
        else:
            print("❌ No wallet found for creator")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def test_linked_accounts():
    """Test 3: Check for existing linked accounts"""
    print_header("TEST 3: Existing Linked Accounts")
    
    linked = supabase.table("linked_accounts").select("*").execute()
    
    if linked.data:
        print(f"✅ Found {len(linked.data)} linked account(s):")
        for acc in linked.data:
            print(f"\n   Platform: {acc.get('platform')}")
            print(f"   Platform User ID: {acc.get('platform_user_id')}")
            print(f"   Laissez User ID: {acc.get('laissez_user_id')[:30]}...")
            
            # Check if this user has wallet
            try:
                user_data = privy_client.users.get(acc.get('laissez_user_id'))
                for account in user_data.linked_accounts:
                    if account.type == "wallet" and hasattr(account, 'address'):
                        print(f"   Wallet: {account.address}")
                        delegated = getattr(account, 'delegated', False)
                        print(f"   Delegated: {delegated}")
                        
                        balance = await check_usdc_balance(account.address)
                        if balance is not None:
                            print(f"   Balance: {balance:.6f} USDC")
            except Exception as e:
                print(f"   ⚠️  Could not fetch wallet: {e}")
        
        return linked.data
    else:
        print("ℹ️  No linked accounts found")
        print("   → First telegram message will trigger account linking")
        return []


async def test_agent_url(agent_url):
    """Test 4: Verify agent URL is working"""
    print_header("TEST 4: Agent URL Test")
    
    print(f"Testing: {agent_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                agent_url,
                json={"input": "Hello, test message"}
            )
            
            if response.status_code == 200:
                data = response.json()
                output = data.get('output', '')
                print(f"✅ Agent URL is working!")
                print(f"   Response preview: {output[:100]}...")
                return True
            else:
                print(f"❌ Agent returned status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"❌ Error calling agent: {e}")
        return False


async def test_webhook_endpoint():
    """Test 5: Test webhook endpoint is accessible"""
    print_header("TEST 5: Webhook Endpoint Test")
    
    webhook_url = f"http://localhost:8001/api/telegram-webhook/{BOT_TOKEN}"
    
    print(f"Testing webhook at: {webhook_url[:50]}...")
    
    # Create a test telegram update
    test_update = {
        "message": {
            "from": {"id": 999999999},
            "chat": {"id": 123456789},
            "text": "test"
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=test_update)
            
            if response.status_code == 200:
                print(f"✅ Webhook endpoint is accessible!")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ Webhook returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error calling webhook: {e}")
        return False


async def main():
    print("\n" + "="*70)
    print("  PAYMENT FLOW COMPONENT TESTS")
    print("="*70)
    
    # Test 1: Agent Configuration
    agent = await test_agent_configuration()
    if not agent:
        print("\n❌ Cannot proceed without agent configuration")
        return
    
    # Test 2: Creator Wallet
    creator_wallet = await test_creator_wallet(agent.get('user_id'))
    
    # Test 3: Linked Accounts
    linked_accounts = await test_linked_accounts()
    
    # Test 4: Agent URL
    agent_url_works = await test_agent_url(agent.get('url'))
    
    # Test 5: Webhook Endpoint
    webhook_works = await test_webhook_endpoint()
    
    # Summary
    print_header("SUMMARY & NEXT STEPS")
    
    print("\n✅ Components Status:")
    print(f"   Agent Config: {'✅' if agent else '❌'}")
    print(f"   Creator Wallet: {'✅' if creator_wallet else '❌'}")
    print(f"   Linked Accounts: {len(linked_accounts)} found")
    print(f"   Agent URL: {'✅' if agent_url_works else '❌'}")
    print(f"   Webhook Endpoint: {'✅' if webhook_works else '❌'}")
    
    print("\n📋 Ready for Testing:")
    
    if agent and creator_wallet and agent_url_works and webhook_works:
        print("""
   ✅ ALL COMPONENTS READY!
   
   🧪 You can now test with Telegram:
   
   1. Message your bot from Telegram
   2. If you haven't linked:
      → Bot will send you a link
      → Click it and login with Google
      → Session signers will be added automatically
      
   3. Message the bot again:
      → If balance < $0.001: You'll see insufficient balance message
      → If balance >= $0.001: Payment will be processed automatically
      
   4. Check the transaction on Base Sepolia:
      https://sepolia.basescan.org/tx/[TX_HASH]
      
   📊 To monitor in real-time:
      tail -f /var/log/supervisor/backend.out.log
        """)
    else:
        print("\n   ⚠️  Some components need attention before testing")
        if not creator_wallet:
            print("   → Creator needs to create a wallet")
        if not agent_url_works:
            print("   → Agent URL is not responding")
        if not webhook_works:
            print("   → Webhook endpoint has issues")


if __name__ == "__main__":
    asyncio.run(main())
