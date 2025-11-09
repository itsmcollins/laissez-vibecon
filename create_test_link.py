#!/usr/bin/env python3
"""
Create a test linked account for payment testing
Useful if you want to test with a specific Privy user ID
"""

import sys
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_test_link(telegram_user_id: str, privy_user_id: str):
    """
    Create a linked account entry for testing
    """
    print(f"\n{'='*60}")
    print("CREATE TEST LINKED ACCOUNT")
    print(f"{'='*60}")
    print(f"Telegram User ID: {telegram_user_id}")
    print(f"Privy User ID: {privy_user_id}")
    
    # Check if link already exists
    existing = supabase.table("linked_accounts").select("*").eq(
        "platform", "telegram"
    ).eq("platform_user_id", telegram_user_id).execute()
    
    if existing.data:
        print(f"\n⚠️  Link already exists!")
        print(f"   Current Privy User: {existing.data[0]['laissez_user_id']}")
        
        response = input("\nUpdate to new Privy user? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        
        # Update existing
        supabase.table("linked_accounts").update({
            "laissez_user_id": privy_user_id
        }).eq("platform", "telegram").eq("platform_user_id", telegram_user_id).execute()
        
        print(f"✅ Updated linked account")
    else:
        # Create new
        link_data = {
            "laissez_user_id": privy_user_id,
            "platform": "telegram",
            "platform_user_id": telegram_user_id
        }
        
        result = supabase.table("linked_accounts").insert(link_data).execute()
        
        if result.data:
            print(f"✅ Created linked account")
        else:
            print(f"❌ Failed to create link")
            return
    
    print(f"\n✅ Test link is ready!")
    print(f"\nNow you can:")
    print(f"1. Message the Telegram bot from account: {telegram_user_id}")
    print(f"2. Bot will use Privy user: {privy_user_id}")
    print(f"3. Payment will be deducted from that user's wallet")


def list_existing_links():
    """Show all existing linked accounts"""
    print(f"\n{'='*60}")
    print("EXISTING LINKED ACCOUNTS")
    print(f"{'='*60}")
    
    links = supabase.table("linked_accounts").select("*").execute()
    
    if links.data:
        for idx, link in enumerate(links.data, 1):
            print(f"\n{idx}. Platform: {link.get('platform')}")
            print(f"   Platform User: {link.get('platform_user_id')}")
            print(f"   Privy User: {link.get('laissez_user_id')[:40]}...")
    else:
        print("\nNo linked accounts found.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - show help
        print(f"\n{'='*60}")
        print("CREATE TEST LINKED ACCOUNT")
        print(f"{'='*60}")
        print("\nUsage:")
        print("  python3 create_test_link.py <telegram_user_id> <privy_user_id>")
        print("\nExamples:")
        print("  # Create link for Telegram user 123456789")
        print("  python3 create_test_link.py 123456789 did:privy:cm...")
        print("\n  # List existing links")
        print("  python3 create_test_link.py list")
        print("\nNote: You can get Privy user ID from database or Privy dashboard")
        
    elif len(sys.argv) == 2 and sys.argv[1] == "list":
        list_existing_links()
        
    elif len(sys.argv) == 3:
        telegram_user_id = sys.argv[1]
        privy_user_id = sys.argv[2]
        create_test_link(telegram_user_id, privy_user_id)
        
    else:
        print("Invalid arguments. Use: create_test_link.py <telegram_user_id> <privy_user_id>")
        print("Or: create_test_link.py list")
