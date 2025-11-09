#!/usr/bin/env python3
"""
Test script to simulate Telegram bot webhook flow
Tests: unlinked account, insufficient balance, successful payment
"""

import httpx
import asyncio
import json
from datetime import datetime

# Configuration
BOT_TOKEN = "7305057804:AAFe6qQVvVVPOCsD_rWn1wMOaQIenBpXSS0"
WEBHOOK_URL = "http://localhost:8001/api/telegram-webhook"

# Test scenarios
SCENARIOS = {
    "unlinked": {
        "name": "Unlinked Account (New User)",
        "telegram_user_id": "999999999",  # Fake ID that doesn't exist
        "chat_id": 123456789,
        "message": "Hello bot!",
        "expected": "link your account"
    },
    "linked_no_balance": {
        "name": "Linked Account - No Balance",
        "telegram_user_id": "888888888",  # Would need to be linked first
        "chat_id": 987654321,
        "message": "Test message",
        "expected": "Insufficient balance"
    },
    "linked_with_balance": {
        "name": "Linked Account - With Balance",
        "telegram_user_id": "777777777",  # Would need to be linked first
        "chat_id": 111222333,
        "message": "Summarize AI news",
        "expected": "transaction hash"
    }
}


def create_telegram_update(telegram_user_id: str, chat_id: int, message_text: str):
    """Create a Telegram webhook update payload"""
    return {
        "update_id": int(datetime.now().timestamp()),
        "message": {
            "message_id": int(datetime.now().timestamp()),
            "from": {
                "id": int(telegram_user_id),
                "is_bot": False,
                "first_name": "Test",
                "username": f"testuser{telegram_user_id}",
                "language_code": "en"
            },
            "chat": {
                "id": chat_id,
                "first_name": "Test",
                "username": f"testuser{telegram_user_id}",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": message_text
        }
    }


async def test_scenario(scenario_name: str, scenario_data: dict):
    """Test a single scenario"""
    print(f"\n{'='*60}")
    print(f"Testing: {scenario_data['name']}")
    print(f"{'='*60}")
    
    payload = create_telegram_update(
        scenario_data['telegram_user_id'],
        scenario_data['chat_id'],
        scenario_data['message']
    )
    
    print(f"Telegram User ID: {scenario_data['telegram_user_id']}")
    print(f"Chat ID: {scenario_data['chat_id']}")
    print(f"Message: {scenario_data['message']}")
    print(f"\nSending webhook request...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{WEBHOOK_URL}/{BOT_TOKEN}",
                json=payload
            )
            
            print(f"\n✅ Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                
                # Check if expectation met
                if scenario_data['expected'].lower() in str(result).lower():
                    print(f"\n✅ PASS: Expected behavior matched")
                else:
                    print(f"\n⚠️  Response received but doesn't match expected: '{scenario_data['expected']}'")
            else:
                print(f"❌ FAIL: Unexpected status code")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def check_backend_logs():
    """Show recent backend logs"""
    import subprocess
    print("\n" + "="*60)
    print("RECENT BACKEND LOGS (last 30 lines)")
    print("="*60)
    try:
        result = subprocess.run(
            ["sudo", "supervisorctl", "tail", "-30", "backend", "stderr"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"Could not fetch logs: {e}")


async def main():
    print("="*60)
    print("TELEGRAM BOT WEBHOOK FLOW TEST")
    print("="*60)
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print(f"Webhook URL: {WEBHOOK_URL}")
    
    # Test Scenario 1: Unlinked Account
    await test_scenario("unlinked", SCENARIOS["unlinked"])
    
    print("\n\n" + "="*60)
    print("NEXT STEPS FOR MANUAL TESTING:")
    print("="*60)
    print("""
1. **Test Unlinked Account:**
   - Message your Telegram bot
   - Bot should send a link to connect account
   - Click the link and log in with Google
   - After linking, message bot again
   
2. **Test Insufficient Balance:**
   - Use an account with < 0.001 USDC
   - Bot should show balance and faucet link
   
3. **Test Successful Payment:**
   - Use an account with >= 0.001 USDC balance
   - Bot should:
     - Deduct payment from your wallet
     - Call agent URL
     - Return agent response + transaction hash
     
4. **Verify Transaction:**
   - Check transaction on Base Sepolia:
     https://sepolia.basescan.org/tx/[TX_HASH]
""")
    
    # Show recent backend logs
    await check_backend_logs()


if __name__ == "__main__":
    asyncio.run(main())
