#!/usr/bin/env python3
"""
Migration script to add creator_wallet_address column to agents table for x402 payments
"""

print("\n" + "=" * 80)
print("AGENTS TABLE MIGRATION: Add Wallet Address for x402 Payments")
print("=" * 80)
print("\nThis migration adds a 'creator_wallet_address' column to store the agent creator's wallet.")
print("This wallet address receives x402 payments when users message the agent.")
print("\nPlease run the following SQL in your Supabase SQL Editor:\n")

sql = """
-- Add creator_wallet_address column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS creator_wallet_address TEXT;

-- Optionally add a comment to document the purpose
COMMENT ON COLUMN agents.creator_wallet_address IS 'EVM wallet address (Base Sepolia) that receives x402 payments for this agent';
"""

print("-" * 80)
print(sql)
print("-" * 80)
print("\nSteps:")
print("1. Go to: Supabase Dashboard > SQL Editor > New Query")
print("2. Copy the SQL above")
print("3. Paste and click 'Run'")
print("\nNote: This column stores the agent creator's Privy wallet address on Base Sepolia.")
print("Payments for using this agent will be sent to this wallet address via x402 protocol.")
print("=" * 80 + "\n")
