# Quick Start: Test the Session Signer Fix

## TL;DR - What to Test

### 1️⃣ New User Test (3 minutes)
```
1. Open Incognito browser
2. Message Telegram bot: "hello"
3. Click link from bot
4. Login with Google
5. Open browser console (F12)
6. Check for: ✅ "Session signers added successfully"
7. Check for: ❌ NO "Duplicate signer" error
8. Message bot again: "test"
9. Verify payment + agent response
```

### 2️⃣ Returning User Test (1 minute)
```
1. Use same browser/account from test 1
2. Visit link page again (from Telegram or directly)
3. Open browser console (F12)
4. Check for: ✅ "already has session signers, skipping"
5. Check for: ❌ NO "Duplicate signer" error
6. Check for: ✅ NO addSessionSigners API call
```

## What Changed

**Before**: Always tried to add signers → Duplicate error
**After**: Check if delegated first → Skip if already set

## Expected Results

| Scenario | Should See | Should NOT See |
|----------|-----------|----------------|
| New user | "Session signers added successfully" | "Duplicate signer" error |
| Returning user | "already has session signers, skipping" | "Duplicate signer" error |
| Payment | Transaction hash link in Telegram | Payment failed error |

## Files Modified

- ✏️ `/app/frontend/src/pages/LinkAccountPage.jsx` (the fix)
- 📝 `/app/SESSION_SIGNER_FIX_SUMMARY.md` (technical details)
- 📘 `/app/USER_TESTING_GUIDE.md` (detailed testing steps)
- 🧪 `/app/verify_session_signer_fix.js` (logic verification - passed ✅)

## Quick Commands

```bash
# Check frontend status
sudo supervisorctl status frontend

# Watch backend logs
sudo supervisorctl tail -f backend stderr

# Restart services (if needed)
sudo supervisorctl restart all
```

## Ready to Test? 

Follow **USER_TESTING_GUIDE.md** for detailed step-by-step instructions.

Report back with any errors or unexpected behavior! 🚀
