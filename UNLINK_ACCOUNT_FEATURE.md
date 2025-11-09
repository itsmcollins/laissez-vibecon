# Unlink Account Feature Implementation

## Summary
Added functionality to view and unlink linked accounts (e.g., Telegram) to allow users to test the linking flow multiple times.

## Changes Made

### Backend (`/app/backend/server.py`)

1. **GET `/api/linked-accounts`** - Fetch all linked accounts for authenticated user
   - Returns: List of linked accounts with platform, platform_user_id, created_at
   - Protected: Requires Privy authentication token

2. **DELETE `/api/linked-accounts/{account_id}`** - Unlink a specific account
   - Validates account belongs to the authenticated user
   - Removes the account from `linked_accounts` table
   - Protected: Requires Privy authentication token

### Frontend (`/app/frontend/src/pages/AgentConfigPage.jsx`)

1. **New State Management**
   - `linkedAccounts` - Stores fetched linked accounts
   - `loadingAccounts` - Loading state for accounts fetch
   - `unlinkingId` - Tracks which account is being unlinked

2. **New Functions**
   - `fetchLinkedAccounts()` - Fetches linked accounts on component mount
   - `handleUnlinkAccount(accountId)` - Handles account unlinking with confirmation

3. **New UI Section: "Linked Accounts"**
   - Displays all linked platform accounts
   - Shows platform name, user ID, and link date
   - Unlink button for each account with confirmation dialog
   - Empty state when no accounts are linked
   - Proper loading states

## How to Test

### 1. View Linked Accounts
1. Open the application in your browser
2. Sign in with Google (Privy)
3. Navigate to the main page (Agent Configuration)
4. Scroll down to see the "Linked Accounts" section
5. You should see any previously linked accounts (e.g., Telegram)

### 2. Unlink an Account
1. In the "Linked Accounts" section, find your linked account
2. Click the "Unlink" button (trash icon)
3. Confirm the action in the dialog
4. The account should be removed from the list
5. You'll see a success toast notification

### 3. Test the Linking Flow Again
1. After unlinking your Telegram account:
2. Open Telegram and send a message to your bot
3. Click the linking URL provided
4. Complete the authentication flow
5. Verify the session signer setup completes without duplicate errors
6. Check backend logs to confirm: "✓ Account linked for user..."
7. The linked account should appear again in the UI

### 4. Verify Backend Endpoints (Optional - requires Privy token)

```bash
# Get linked accounts (requires valid Privy JWT token)
curl -H "Authorization: Bearer YOUR_PRIVY_TOKEN" \
  http://localhost:8001/api/linked-accounts

# Delete a linked account (requires valid Privy JWT token)
curl -X DELETE \
  -H "Authorization: Bearer YOUR_PRIVY_TOKEN" \
  http://localhost:8001/api/linked-accounts/ACCOUNT_ID
```

## Database Schema
The feature uses the existing `linked_accounts` table:
```sql
CREATE TABLE linked_accounts (
  id SERIAL PRIMARY KEY,
  laissez_user_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  platform_user_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(platform, platform_user_id)
);
```

## Security
- All endpoints are protected with Privy JWT authentication
- Users can only view and unlink their own accounts
- DELETE endpoint verifies account ownership before deletion
- Frontend includes confirmation dialog before unlinking

## UI/UX Features
- Clear visual distinction for each linked account
- Platform name displayed (e.g., "Telegram")
- Platform user ID shown for identification
- Date when account was linked
- Loading states during fetch and unlink operations
- Success/error toast notifications
- Empty state when no accounts are linked
- Responsive design matching existing UI patterns

## Notes
- Session signers are managed by Privy on the frontend
- Unlinking an account does NOT remove Privy session signers (these are managed separately)
- Users will need to re-authenticate and re-add session signers when linking again
- The fix from Codex (linkingInProgressRef, completedCodeRef) prevents duplicate signer issues
