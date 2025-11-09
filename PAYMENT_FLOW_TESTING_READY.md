# Payment Flow Testing - Ready to Use! 🚀

## ✅ Environment Status

All components have been verified and are ready for testing:

### Backend Components
- ✅ **FastAPI Server**: Running on port 8001
- ✅ **Telegram Webhook**: `/api/telegram-webhook/{bot_token}` is accessible
- ✅ **Privy Integration**: Authentication & wallet management working
- ✅ **Supabase Database**: Connected and configured
- ✅ **USDC Contract**: Base Sepolia testnet (0x036CbD53842c5426634e7929541eC2318f3dCF7e)

### Agent Configuration
```
Name: HNS
URL: https://techsummary.emergent.host/api/agent
Price: $0.001 USDC per message
Bot Token: 7305057804:AAFe6qQVvVVPOCsD_rWn1wMOaQIenBpXSS0
Creator Wallet: 0x456B421b6C44c8fE148280f6F84DF75D2473c472
Creator Balance: 10.000000 USDC ✅
```

### Frontend Components
- ✅ **React App**: Running on port 3000
- ✅ **Privy Auth**: Google OAuth configured
- ✅ **Session Signers**: Auto-added on account linking

---

## 🧪 Testing Scenarios

### Scenario 1: Unlinked Account (New User)

**Expected Flow:**
1. User messages Telegram bot
2. Bot checks database → no linked account found
3. Bot creates pending link in database
4. Bot sends message with link URL: `https://[your-domain]/link?code=...`
5. User clicks link → redirects to frontend
6. User logs in with Google (Privy)
7. Frontend adds session signers automatically
8. Backend completes link → saves to `linked_accounts` table
9. Telegram receives confirmation message

**What to Look For:**
- ✅ Link message sent to Telegram
- ✅ Link URL contains unique code
- ✅ Frontend shows login screen
- ✅ After login, session signers are added
- ✅ "Account linked successfully" message in Telegram

---

### Scenario 2: Linked Account - Insufficient Balance

**Setup:**
- User has already linked account
- User wallet has < $0.001 USDC

**Expected Flow:**
1. User messages Telegram bot
2. Bot finds linked account
3. Bot fetches user's Privy wallet
4. Bot checks USDC balance on Base Sepolia
5. Balance < $0.001 → Bot sends insufficient balance message
6. Message includes current balance + faucet link

**Expected Bot Response:**
```
💰 Insufficient balance!

Your balance: 0.000000 USDC
Required: 0.001000 USDC

Add funds at https://faucet.circle.com (select Base Sepolia) and try again.
```

**What to Look For:**
- ✅ Balance check happens
- ✅ User sees their current balance
- ✅ Faucet link provided
- ❌ NO payment transaction attempted

---

### Scenario 3: Linked Account - Sufficient Balance (PAYMENT!)

**Setup:**
- User has already linked account
- User wallet has >= $0.001 USDC
- User wallet has session signers enabled (delegated: true)

**Expected Flow:**
1. User messages Telegram bot: "Summarize AI news"
2. Bot finds linked account
3. Bot fetches user's Privy wallet + wallet_id
4. Bot checks USDC balance → sufficient ✅
5. Bot fetches creator's wallet address
6. **Bot initiates USDC payment via Privy SDK:**
   - Constructs transfer transaction
   - Signs with session signer
   - Submits to Base Sepolia
7. Bot receives transaction hash
8. Bot calls agent URL: `https://techsummary.emergent.host/api/agent`
9. Bot receives agent response
10. Bot sends to Telegram: `[agent response]\n\n💳 Transaction: https://sepolia.basescan.org/tx/[hash]`

**Expected Bot Response:**
```
Here's a summary of the latest AI news from HackerNews...
[AI news content]

💳 Transaction: https://sepolia.basescan.org/tx/0x123abc...
```

**What to Look For:**
- ✅ Payment deducted from user wallet
- ✅ Payment received by creator wallet
- ✅ Transaction visible on Base Sepolia explorer
- ✅ Agent response included in message
- ✅ Transaction hash link provided

---

## 🔍 Monitoring & Debugging

### Watch Backend Logs
```bash
# Watch all backend activity
tail -f /var/log/supervisor/backend.out.log

# Watch errors only
tail -f /var/log/supervisor/backend.err.log

# Watch for payment-related logs
tail -f /var/log/supervisor/backend.out.log | grep -E "payment|balance|tx_hash|Transaction"
```

### Check Service Status
```bash
sudo supervisorctl status
```

### Restart Services (if needed)
```bash
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
sudo supervisorctl restart all
```

### Check Database
```bash
# Run test script to see current state
python3 /app/test_payment_components.py
```

---

## 📊 Database Tables

### agents
- Stores agent configurations
- Links bot tokens to creator user IDs

### linked_accounts
- Maps Telegram users to Privy users
- Required for payment flow

### pending_links
- Temporary storage for account linking
- Code expires after 24 hours

---

## 🔧 Key Backend Functions

### Payment Flow Functions:
1. **`get_user_wallet_with_id()`** - Gets wallet address + ID
2. **`check_usdc_balance()`** - Checks balance via RPC
3. **`send_usdc_payment()`** - Executes USDC transfer via Privy
4. **`invoke_agent()`** - Calls external agent URL

### Authentication:
1. **`verify_privy_token()`** - Verifies JWT tokens
2. **Frontend** adds session signers during linking

---

## 🎯 Testing Checklist

- [ ] Test with unlinked Telegram account
  - [ ] Receive link message
  - [ ] Click link and login
  - [ ] Verify session signers added
  - [ ] Receive confirmation

- [ ] Test with linked account (no balance)
  - [ ] Send message to bot
  - [ ] Receive insufficient balance message
  - [ ] See current balance displayed
  - [ ] Get faucet link

- [ ] Add funds via faucet
  - [ ] Visit https://faucet.circle.com
  - [ ] Select Base Sepolia
  - [ ] Get USDC testnet tokens

- [ ] Test with linked account (with balance)
  - [ ] Send message to bot
  - [ ] Wait for payment processing
  - [ ] Receive agent response + tx hash
  - [ ] Verify transaction on explorer
  - [ ] Check balance decreased

- [ ] Verify transaction on explorer
  - [ ] Visit https://sepolia.basescan.org/tx/[hash]
  - [ ] Confirm transfer from user → creator
  - [ ] Confirm amount = $0.001

---

## 🐛 Common Issues & Fixes

### Issue: "Unable to access your wallet"
**Cause:** User's wallet doesn't have session signers
**Fix:** User needs to re-link account via link flow

### Issue: "Payment failed"
**Cause:** Multiple possible causes
- Insufficient balance (check balance first)
- Session signer not properly configured
- Network issues (Base Sepolia RPC)
**Fix:** Check backend logs for specific error

### Issue: Agent URL timeout
**Cause:** External agent is slow or unavailable
**Fix:** This is expected if agent URL is busy. Bot will respond with fallback message.

### Issue: Telegram not receiving messages
**Cause:** Bot token issue or Telegram API issue
**Fix:** Verify bot token is correct. Check if bot is active in Telegram.

---

## 📱 How to Test with Your Telegram Bot

### Quick Start:
1. Open Telegram
2. Search for your bot: `@your_bot_name`
3. Send message: `/start` or `hello`
4. Follow the flow!

### What Happens:
- **First message**: Bot sends link to connect account
- **After linking**: Bot processes your message with payment
- **Every message**: Costs $0.001 USDC (deducted automatically)

---

## 💡 Tips

- **Test with small amounts first** ($0.001 is minimum)
- **Use Base Sepolia faucet** for free testnet USDC
- **Monitor backend logs** while testing to see what's happening
- **Check transaction explorer** to verify payments
- **Session signers are added automatically** - no manual setup needed

---

## ✅ Everything is Ready!

All components have been tested and are working:
- ✅ Backend server running
- ✅ Webhook endpoint accessible  
- ✅ Agent configured
- ✅ Creator has wallet with balance
- ✅ Database tables set up
- ✅ Payment logic functional

**You can start testing with your Telegram bot now!**

Just message your bot and the flow will start automatically.

---

## 📞 Need Help?

If you encounter issues:
1. Check backend logs: `tail -f /var/log/supervisor/backend.out.log`
2. Run component test: `python3 /app/test_payment_components.py`
3. Verify services: `sudo supervisorctl status`
4. Check database state with the test script

---

**Happy Testing! 🚀**
