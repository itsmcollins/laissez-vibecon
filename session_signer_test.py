#!/usr/bin/env python3
"""
Specific test for Session Signer functionality
"""

import requests
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "https://agent-payment-api.preview.emergentagent.com")

def test_session_signer_issue():
    """Test to verify the session signer issue found in logs"""
    print("🔍 Testing Session Signer Issue...")
    
    # Use the existing linked user from the database
    bot_token = "7305057804:AAFe6qQVvVVPOCsD_rWn1wMOaQIenBpXSS0"
    telegram_user_id = "8249022962"  # This user is linked to did:privy:cmhrbdcpy007jk00c2mci53fp
    
    test_payload = {
        "message": {
            "chat": {"id": 123456789},
            "from": {"id": int(telegram_user_id)},
            "text": "Test payment flow with session signers"
        }
    }
    
    print(f"Testing with linked user: {telegram_user_id}")
    print(f"Expected behavior: Payment should fail because wallet is 'not delegated'")
    print(f"Wallet address from logs: 0x456B421b6C44c8fE148280f6F84DF75D2473c472")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/telegram-webhook/{bot_token}",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        
        # Check backend logs for the specific error
        print("\n🔍 Expected in backend logs:")
        print("   - '💰 Payment required: $0.001 USDC'")
        print("   - 'Fetching user data with wallet ID for: did:privy:cmhrbdcpy0...'")
        print("   - '⚠️  Wallet 0x456B421b6C44c8fE148280f6F84DF75D2473c472 found but not delegated'")
        print("   - This indicates session signers were NOT added during account linking")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_session_signer_issue()
    print(f"\nTest result: {'✅ PASS' if success else '❌ FAIL'}")