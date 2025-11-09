# User Testing Guide: Session Signer Fix

## What Was Fixed

The application was generating "Duplicate signer" errors because it tried to add session signers every time, even when a wallet was already delegated. This has been fixed to:

1. ✅ Check if wallet is already delegated BEFORE attempting to add signers
2. ✅ Skip the API call for returning users (faster, cleaner)
3. ✅ Eliminate "Duplicate signer" errors from console
4. ✅ Show appropriate toast messages for each scenario

## Testing Scenarios

### 🧪 Scenario 1: New User (First Time Linking)

**Goal**: Verify session signers are added correctly for new users

**Steps**:
1. Open a **new Incognito/Private browser window**
2. Send a message to your Telegram bot (e.g., "hello")
3. Bot should respond with a link to connect your account
4. Click the link (opens the web app)
5. Authenticate with Google
6. **Open browser DevTools** (F12) and check the **Console** tab

**Expected Console Output**:
```
=== SESSION SIGNER SETUP START ===
KEY_QUORUM_ID: wsu5txzij9hcntkyf9rfw5zh
Found wallet account: {type: 'wallet', address: '0x...', delegated: false}
⏳ Adding session signer to wallet: 0x...
Wallet delegated status: false
Calling addSessionSigners with: {...}
✅ Session signers added successfully!
=== SESSION SIGNER SETUP END ===
📡 Calling backend to complete account link...
✅ Backend link complete successful
```

**Expected Behavior**:
- ✅ Toast: "Wallet configured for payments"
- ✅ Toast: "Account linked"
- ✅ **NO "Duplicate signer" error**
- ✅ Redirect to home page after ~2 seconds

7. Send another message to the bot (e.g., "test payment")
8. Bot should process payment and respond

**Expected Telegram Response**:
```
💸 Payment successful! (0.001 USDC)
View transaction: https://sepolia.basescan.org/tx/0x...

[Agent response here]
```

---

### 🧪 Scenario 2: Returning User (Already Delegated)

**Goal**: Verify no duplicate errors for users with already-delegated wallets

**Steps**:
1. Using the **same account from Scenario 1**, visit the link page again:
   - Option A: Click the link in Telegram again
   - Option B: Navigate to: `https://payment-flow-check.preview.emergentagent.com/link?code=YOUR_CODE`
2. **Open browser DevTools** (F12) and check the **Console** tab

**Expected Console Output**:
```
=== SESSION SIGNER SETUP START ===
KEY_QUORUM_ID: wsu5txzij9hcntkyf9rfw5zh
Found wallet account: {type: 'wallet', address: '0x...', delegated: true}
✅ Wallet already has session signers (delegated: true), skipping addSessionSigners
Wallet address: 0x...
=== SESSION SIGNER SETUP END ===
📡 Calling backend to complete account link...
✅ Backend link complete successful
```

**Expected Behavior**:
- ✅ Toast: "Wallet already configured for payments"
- ✅ Toast: "Account linked"
- ✅ **NO "Duplicate signer" error**
- ✅ **NO call to `addSessionSigners()` API**
- ✅ Faster linking process (skips API call)

---

### 🧪 Scenario 3: Complete Payment Flow (End-to-End)

**Goal**: Verify the entire payment flow works correctly

**Prerequisites**:
- Your wallet has USDC (get from https://faucet.circle.com if needed)
- Your wallet is linked and delegated (from Scenario 1)

**Steps**:
1. Send a message to your Telegram bot: "hello"
2. Wait for bot response

**Expected Telegram Response**:
```
💸 Payment successful! (0.001 USDC)
View transaction: https://sepolia.basescan.org/tx/0x[hash]

[Agent response to your message]
```

**Verification**:
- ✅ Payment goes through without errors
- ✅ Transaction hash link is clickable and valid
- ✅ Agent responds with appropriate message
- ✅ No error messages in Telegram

---

## Checklist: What to Look For

### ✅ Console Logs (Browser DevTools)
- [ ] No "Duplicate signer(s)" errors
- [ ] Appropriate "skipping" message for returning users
- [ ] "Session signers added successfully" only for new users
- [ ] Clean, predictable log output

### ✅ Toast Notifications
- [ ] "Wallet configured for payments" appears
- [ ] "Account linked" appears
- [ ] No error toasts (unless real errors occur)

### ✅ Telegram Bot
- [ ] Link messages include agent name and price
- [ ] Payment success messages include transaction hash link
- [ ] Agent responds after successful payment
- [ ] Insufficient balance shows faucet link

### ✅ Performance
- [ ] Returning users link faster (no unnecessary API call)
- [ ] No delays or hanging during link process

---

## Troubleshooting

### If you see "Duplicate signer" error:
- Clear browser cache and try again
- Use Incognito/Private mode
- Check that frontend was restarted (should be done already)

### If payment fails:
- Verify you have USDC in your wallet
- Check https://faucet.circle.com for testnet USDC
- Check backend logs: `sudo supervisorctl tail -f backend stderr`

### If link page shows error:
- Check that link code is valid
- Try authenticating with Google again
- Check browser console for specific errors

---

## Backend Logs (Optional)

To monitor backend during testing:

```bash
# Watch backend logs in real-time
sudo supervisorctl tail -f backend stderr

# Check recent backend logs
tail -n 100 /var/log/supervisor/backend.err.log
```

---

## Success Criteria

The fix is successful if:

1. ✅ **New users**: Session signers are added correctly, no errors
2. ✅ **Returning users**: No "Duplicate signer" error, faster link process
3. ✅ **Payment flow**: End-to-end payment works for both scenarios
4. ✅ **Console**: Clean, predictable logs without duplicate errors
5. ✅ **User experience**: Smooth linking and payment process

---

## After Testing

Please report:
1. Which scenarios you tested (1, 2, 3, or all)
2. Any errors or unexpected behavior
3. Screenshots of console logs (especially if errors occur)
4. Telegram bot responses (for scenario 3)

If everything works as expected, we can mark this task as complete! 🎉
