# Payment Debug Logging - Enhanced

## Overview
Added comprehensive logging throughout the payment flow to help debug payment failures when sending subsequent messages after linking.

## Enhanced Logging Areas

### 1. Telegram Webhook Entry Point
**Location:** `/api/telegram-webhook/{bot_token}` (line ~987)

**What's Logged:**
```
=================================================================================
🔔 TELEGRAM WEBHOOK RECEIVED
=================================================================================
📋 Bot Token: [first 20 chars]...
📋 Timestamp: [ISO timestamp]
📨 Message Details:
   From Telegram User: [telegram_user_id]
   Chat ID: [chat_id]
   Message: [first 100 chars]...
=================================================================================
```

**Purpose:** Track every incoming message and identify which user/chat it's from

### 2. Account Link Check
**Location:** After webhook receives message

**What's Logged:**
```
🔍 Checking if Telegram user [id] is linked...
📊 Query result: Found [n] linked accounts
```

**Two Paths:**
- ❌ NOT linked → Creates pending link
- ✅ Linked → Proceeds to payment flow

### 3. User Wallet Retrieval with ID
**Location:** `get_user_wallet_with_id()` function (line ~222)

**What's Logged:**
```
🔍 Fetching user data with wallet ID for: [user_id]...
📋 User has [n] linked accounts
  Account 0: type=[type], chain_type=[chain]
  📍 Found Ethereum wallet:
     Address: [wallet_address]
     ID: [wallet_id]
     Delegated: [true/false]
```

**Key Checks:**
- ✅ Wallet found AND delegated → Returns wallet info
- ⚠️ Wallet found but NOT delegated → Returns None (session signers missing)
- ❌ No wallet found → Returns None

### 4. Payment Function - MOST DETAILED
**Location:** `send_usdc_payment()` function (line ~334)

**What's Logged:**
```
============================================================
💸 PAYMENT FUNCTION START
============================================================
📋 Payment Details:
   From Wallet ID: [wallet_id...]
   From Address: [wallet_address]
   To Address: [recipient_address]
   Amount: $[amount] USDC
   Amount (atomic): [amount_with_decimals] (with 6 decimals)
📝 Transaction data encoded: [hex_data]...
📡 Calling Privy RPC API...
   URL: https://api.privy.io/v1/wallets/[id].../rpc
   Method: eth_sendTransaction
   Network: Base Sepolia (Chain ID: 84532)
   USDC Contract: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
   Gas Sponsorship: Enabled
📬 Response Status: [status_code]
```

**Success Path:**
```
✅ Response Body: {...}
✅✅✅ TRANSACTION SENT SUCCESSFULLY!
   Transaction Hash: [tx_hash]
   View on BaseScan: https://sepolia.basescan.org/tx/[tx_hash]
============================================================
```

**Failure Path:**
```
❌ TRANSACTION FAILED!
   Status Code: [code]
   Response Text: [error_message]
   Error JSON: [parsed_error]
============================================================
```

**Exception Path:**
```
❌❌❌ EXCEPTION in send_usdc_payment: [error]
   Exception Type: [type]
   Stack Trace:
   [full traceback]
============================================================
```

### 5. Balance Checking
**Location:** Throughout payment flow

**What's Logged:**
```
💵 Checking USDC balance for [address]...
💰 Buyer balance: $[balance] USDC
```

**If Insufficient:**
```
⚠️  Insufficient balance: $[balance] < $[required]
```

### 6. Wallet Resolution
**Location:** Before payment

**What's Logged:**
```
🔍 Getting buyer's wallet for user: [user_id]...
✅ Buyer wallet: [address] (ID: [wallet_id]...)

🔍 Getting creator's wallet for user: [creator_id]...
✅ Creator wallet: [address]
```

**If Failed:**
```
❌ Could not find your delegated wallet
❌ Creator wallet not found
```

### 7. Agent Response Flow
**Location:** After payment succeeds

**What's Logged:**
```
📡 Calling agent URL: [url]
✅ Agent response received
✅ Added transaction hash to response
```

## How to Read the Logs

### To Monitor Live Payment Flow:
```bash
# Watch backend logs in real-time
tail -f /var/log/supervisor/backend.*.log

# Or filter for payment-related logs
tail -f /var/log/supervisor/backend.*.log | grep -E "(PAYMENT|💸|💳|❌|✅)"
```

### Common Error Patterns to Look For:

#### 1. Wallet Not Delegated
```
⚠️  Wallet [address] found but NOT delegated (session signers not added)
```
**Fix:** User needs to re-link account via Telegram link

#### 2. Payment API Failure
```
❌ TRANSACTION FAILED!
   Status Code: 400/401/403/500
   Response Text: [check this for details]
```
**Check:** 
- Privy API credentials valid?
- Authorization key correct?
- Wallet has session signers?

#### 3. Insufficient Balance
```
⚠️  Insufficient balance: $0.000000 < $0.001000
```
**Fix:** User needs to fund wallet at faucet.circle.com

#### 4. Wallet Not Found
```
❌ No delegated wallet found for user [id]
```
**Fix:** User needs to create wallet and link account

## Testing Workflow

1. **Send first message to bot** (before linking)
   - Look for: "❌ Telegram user NOT linked"
   - Should create pending link

2. **Click link and authenticate**
   - Look for: "✓ Account linked for user"
   - Look for: "✅ Found delegated wallet" in LinkAccountPage

3. **Send subsequent message** (the failing one)
   - Look for: "🔔 TELEGRAM WEBHOOK RECEIVED"
   - Look for: "✅ Telegram user [id] linked to Privy user"
   - Look for: "💸 PAYMENT FUNCTION START"
   - **Watch for:** Any ❌ errors in the payment flow

4. **Check for success**
   - Look for: "✅✅✅ TRANSACTION SENT SUCCESSFULLY!"
   - Look for: Transaction hash in logs

## Log Symbols Legend
- 🔔 Webhook received
- 📨 Message details
- 🔍 Searching/querying
- 📋 Information display
- 💳 Payment required
- 💸 Payment function
- 💵 Balance check
- 💰 Balance amount
- ✅ Success
- ❌ Error/failure
- ⚠️ Warning
- 📡 API call
- 📬 Response received
- 📤 Sending message

## Expected Flow for Working Payment

```
1. 🔔 TELEGRAM WEBHOOK RECEIVED
2. 📨 Message from user [id]
3. 🔍 Checking if linked... → ✅ Linked
4. 📋 Agent found, Price: $0.001
5. 💳 Payment required
6. 🔍 Getting buyer's wallet → ✅ Found
7. 💵 Checking balance → 💰 Sufficient
8. 🔍 Getting creator's wallet → ✅ Found
9. 💸 PAYMENT FUNCTION START
10. 📡 Calling Privy RPC API
11. 📬 Response Status: 200
12. ✅✅✅ TRANSACTION SENT SUCCESSFULLY!
13. 📡 Calling agent URL
14. ✅ Agent response received
15. 📤 Sending response to Telegram
```

## Next Steps

When you send a subsequent message and payment fails:

1. **Check the logs immediately:**
   ```bash
   tail -n 200 /var/log/supervisor/backend.*.log | grep -A 20 "PAYMENT FUNCTION START"
   ```

2. **Look for the failure point:**
   - Is wallet delegated? (Should see "✅ Found delegated wallet")
   - Is balance sufficient? (Should see "💰 Buyer balance: $...")
   - Did Privy API call fail? (Check for "❌ TRANSACTION FAILED!")
   - What's the error message? (Check "Response Text:")

3. **Share the relevant log section** with the specific error for further debugging
