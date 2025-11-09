#!/usr/bin/env python3
"""
Migration script to add user_id column to agents table
"""

print("\n" + "=" * 80)
print("AGENTS TABLE MIGRATION")
print("=" * 80)
print("\nThis migration adds a 'user_id' column to the agents table.")
print("\nPlease run the following SQL in your Supabase SQL Editor:\n")

sql = """
-- Add user_id column to agents table (allow NULL for existing records)
ALTER TABLE agents ADD COLUMN IF NOT EXISTS user_id TEXT;

-- For testing: you can set a test user_id for existing records
-- UPDATE agents SET user_id = 'test-user-id' WHERE user_id IS NULL;
"""

print("-" * 80)
print(sql)
print("-" * 80)
print("\nSteps:")
print("1. Go to: Supabase Dashboard > SQL Editor > New Query")
print("2. Copy the SQL above")
print("3. Paste and click 'Run'")
print("\nNote: The user_id column will be nullable to preserve existing agents.")
print("New agents created through the authenticated API will require user_id.")
print("=" * 80 + "\n")
