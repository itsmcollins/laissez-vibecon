#!/usr/bin/env python3
"""
Setup script to create authentication and linking tables in Supabase
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Supabase credentials not found in .env file")
    exit(1)

print(f"Connecting to Supabase at {supabase_url}...")
supabase = create_client(supabase_url, supabase_key)

# SQL to create all necessary tables
setup_sql = """
-- Create agents table with user_id
CREATE TABLE IF NOT EXISTS agents (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  url TEXT NOT NULL,
  bot_token TEXT NOT NULL,
  price FLOAT NOT NULL DEFAULT 0.001,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create index on user_id for faster queries
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);

-- Create pending_links table for temporary linking codes
CREATE TABLE IF NOT EXISTS pending_links (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  platform TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL
);

-- Create index on code for faster lookups
CREATE INDEX IF NOT EXISTS idx_pending_links_code ON pending_links(code);

-- Create linked_accounts table for permanent account links
CREATE TABLE IF NOT EXISTS linked_accounts (
  id SERIAL PRIMARY KEY,
  laissez_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(platform, platform_id)
);

-- Create index on laissez_id for faster user lookups
CREATE INDEX IF NOT EXISTS idx_linked_accounts_laissez_id ON linked_accounts(laissez_id);

-- Create index on platform and platform_id for faster platform lookups
CREATE INDEX IF NOT EXISTS idx_linked_accounts_platform ON linked_accounts(platform, platform_id);
"""

print("\nPlease run the following SQL in your Supabase SQL Editor:")
print("=" * 80)
print(setup_sql)
print("=" * 80)
print("\nSteps:")
print("1. Go to: Supabase Dashboard > SQL Editor > New Query")
print("2. Copy the SQL above")
print("3. Paste and click 'Run'")
print("\nThis will create the following tables:")
print("  - agents (with user_id for Privy authentication)")
print("  - pending_links (temporary codes for account linking)")
print("  - linked_accounts (permanent platform account links)")

# Try to verify tables exist
print("\n" + "=" * 80)
print("Verifying tables...")
print("=" * 80)

tables_to_check = ["agents", "pending_links", "linked_accounts"]
for table_name in tables_to_check:
    try:
        response = supabase.table(table_name).select("*").limit(1).execute()
        print(f"✓ Table '{table_name}' exists and is accessible")
    except Exception as e:
        print(f"✗ Table '{table_name}' not found or not accessible")
        print(f"  Error: {str(e)}")

print("\n" + "=" * 80)
print("Setup verification complete!")
print("=" * 80)
