# Agent Access Model Change

## Summary

Changed agent access model from **creator-only** to **open access for all authenticated users**.

## What Changed

### Before ❌
```python
# Only the agent creator could send messages
agent_response = supabase.table("agents").select("*").eq(
    "bot_token", bot_token
).eq("user_id", laissez_user_id).execute()  # ← Restricted by user_id
```

**Problem**: If User A created an agent, User B (even if authenticated) couldn't send messages to it.

### After ✅
```python
# Any authenticated user can send messages to any agent
agent_response = supabase.table("agents").select("*").eq(
    "bot_token", bot_token
).execute()  # ← No user_id restriction
```

**Benefit**: If User A creates an agent, any user with a linked Telegram account can send messages to it.

## Access Control Model

### Current Behavior

1. **Agent Creation**: ✅ Still requires authentication
   - Only authenticated users can create agents
   - `user_id` is stored to track who created the agent
   - Uses Privy token verification

2. **Messaging Agents**: ✅ Now open to all authenticated users
   - Any user with a linked Telegram account can message any agent
   - No need to be the creator of the agent
   - Still requires authentication (must complete linking flow)

### Authentication Flow

**For Agent Creation** (POST /api/agents):
```
User → Privy Auth → JWT Token → Backend verifies → Create agent with user_id
```

**For Messaging via Telegram**:
```
Telegram User → Check linked_accounts table → If linked → Allow access to any agent
                                           → If not linked → Send linking URL
```

## Database Schema

### agents table
```sql
CREATE TABLE agents (
  id SERIAL PRIMARY KEY,
  user_id TEXT,              -- Still stored (for tracking/analytics)
  bot_token TEXT NOT NULL,   -- Used for routing messages
  url TEXT NOT NULL,
  price FLOAT DEFAULT 0.001,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Notes**:
- `user_id` is still stored and used for:
  - Tracking which user created which agent
  - Future analytics/billing
  - Displayed in frontend (users see their own agents)
- `user_id` is NOT used for:
  - ❌ Restricting who can message the agent
  - ❌ Filtering agents in Telegram webhook handler

### linked_accounts table
```sql
CREATE TABLE linked_accounts (
  laissez_user_id TEXT NOT NULL,    -- Privy user ID
  platform VARCHAR NOT NULL,         -- "telegram"
  platform_user_id VARCHAR NOT NULL, -- Telegram user ID
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (platform, platform_user_id)
);
```

**Purpose**: 
- Links external platform IDs (Telegram) to Privy user IDs
- Used to verify user is authenticated before allowing access to agents

## Example Scenarios

### Scenario 1: Public Agent
```
1. Alice creates Agent A with bot token "abc123"
2. Alice's Telegram is linked (laissez_user_id = "alice-123")
3. Bob links his Telegram (laissez_user_id = "bob-456")
4. Bob sends message to Agent A → ✅ Works!
5. Charlie (unlinked) sends message to Agent A → ❌ Gets linking URL
```

### Scenario 2: Multiple Users, Multiple Agents
```
1. Alice creates Agent A
2. Bob creates Agent B
3. Both Alice and Bob are linked
4. Alice can message Agent A → ✅ (creator)
5. Alice can message Agent B → ✅ (authenticated user)
6. Bob can message Agent A → ✅ (authenticated user)
7. Bob can message Agent B → ✅ (creator)
```

## No SQL Migration Required

✅ No database changes needed because:
- Table structure remains the same
- We're just removing a filter in the query
- `user_id` column still exists and is populated

## Code Changes

**File**: `/app/backend/server.py`

**Line ~475** (in `telegram_webhook` function):

```python
# REMOVED THIS FILTER: .eq("user_id", laissez_user_id)

# Before:
agent_response = supabase.table("agents").select("*").eq(
    "bot_token", bot_token
).eq("user_id", laissez_user_id).execute()

# After:
agent_response = supabase.table("agents").select("*").eq(
    "bot_token", bot_token
).execute()
```

## Testing

### Test 1: Linked user messaging any agent
```bash
# Setup: Agent created by User A with bot token "xyz"
# Test: User B (linked) sends Telegram message

Expected: 
✓ Backend finds agent by bot_token (ignoring user_id)
✓ Message proxied to agent URL
✓ User B receives response
```

### Test 2: Unlinked user trying to message
```bash
# Setup: Agent created by User A
# Test: User C (not linked) sends Telegram message

Expected:
✓ Backend checks linked_accounts table
✗ User C not found
✓ Creates pending_links record
✓ Sends linking URL to User C
```

## Benefits

1. **Collaboration**: Multiple users can interact with the same agent
2. **Sharing**: Agent creators can share their bot with others
3. **Community**: Enables community-driven agent interactions
4. **Flexibility**: Users can explore different agents without restrictions

## Security

✅ **Still Secure**:
- Must have linked Telegram account (authenticated via Privy)
- Cannot message without completing linking flow
- Agent creators tracked via `user_id`
- Future: Can add per-agent access controls if needed

## Future Enhancements

If you want to add per-agent access control later:

1. Add `is_public` boolean to agents table
2. Add `agent_permissions` table for fine-grained control
3. Check permissions in webhook handler before proxying

But for now, the open model makes sense for a collaborative platform.
