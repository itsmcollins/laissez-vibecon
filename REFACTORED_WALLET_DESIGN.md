# Refactored Wallet Design - Dynamic Fetching from Privy

## Problem with Original Design

The initial implementation tried to:
1. Create wallets programmatically via backend
2. Store `creator_wallet_address` in the database

**Issues:**
- Privy Python SDK doesn't support `pregenerateWallets()` method
- `wallets.create()` requires wallet ID, not user ID
- Database redundancy - wallet address already exists in Privy
- Violates single source of truth principle

## New Design: Dynamic Wallet Fetching

### Architecture
- **NO database column for wallet address**
- Wallets created by users via Privy frontend
- Backend fetches wallet address dynamically from Privy when needed
- Single source of truth: Privy

### Key Functions

#### 1. `get_user_wallet_address(user_id: str) → Optional[str]`
```python
async def get_user_wallet_address(user_id: str) -> Optional[str]:
    """
    Get a user's Privy embedded wallet address.
    Returns the wallet address or None if user has no wallet.
    
    Note: User must have created a wallet via Privy frontend.
    One wallet per user, reused across all their agents.
    """
    user_data = _privy_client.users.get(user_id)
    
    for account in user_data.linked_accounts:
        if account.type == "wallet" and account.chain_type == "ethereum":
            return account.address
    
    return None
```

**Usage:**
- Called when creating agents (validation)
- Called when checking x402 payments (get recipient)
- NO wallet creation - user must have wallet already

#### 2. Agent Creation Flow

```python
@app.post("/api/agents")
async def create_agent_config(...):
    # Validate user has a wallet
    wallet_address = await get_user_wallet_address(user_id)
    
    if not wallet_address:
        raise HTTPException(
            status_code=400,
            detail="No wallet found. Please create an embedded wallet in your Privy account first."
        )
    
    # Store agent WITHOUT wallet address
    data = {
        "user_id": user_id,
        "url": config.url,
        "bot_token": config.bot_token,
        "price": config.price
        # NO creator_wallet_address field
    }
```

#### 3. x402 Payment Check

```python
async def check_x402_payment(request, bot_token):
    # Get agent to find creator user_id
    agent = supabase.table("agents").select("*").eq("bot_token", bot_token).execute()
    creator_user_id = agent.data[0]["user_id"]
    
    # Fetch creator's wallet dynamically from Privy
    creator_wallet = await get_user_wallet_address(creator_user_id)
    
    # Return 402 with payment requirements
    return {
        "status_code": 402,
        "body": {
            "accepts": [{
                "payTo": creator_wallet,  # Dynamically fetched
                ...
            }]
        }
    }
```

### Database Schema

**agents table:**
```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,           -- Privy user ID
    url TEXT NOT NULL,                -- Agent endpoint
    bot_token TEXT NOT NULL,          -- Telegram bot token
    price FLOAT NOT NULL,             -- Price in USD
    created_at TIMESTAMP DEFAULT NOW()
    -- NO creator_wallet_address column needed!
);
```

### Frontend Requirements

**Users must create embedded wallets via Privy UI before creating agents.**

Option 1: Automatic on login
```jsx
import { usePrivy } from '@privy-io/react-auth';

function App() {
  const { user, createWallet } = usePrivy();
  
  useEffect(() => {
    if (user && !user.wallet) {
      createWallet();
    }
  }, [user]);
}
```

Option 2: Manual button
```jsx
<Button onClick={createWallet}>
  Create Wallet
</Button>
```

Option 3: Automatic on agent creation attempt
```jsx
async function handleCreateAgent() {
  if (!user.wallet) {
    await createWallet();
  }
  
  // Now create agent
  await fetch('/api/agents', ...);
}
```

### Benefits

✅ **Single Source of Truth**
- Privy manages wallets, not our database
- No synchronization issues

✅ **Simpler Backend**
- No wallet creation logic
- No database migrations for wallet fields
- Just read-only wallet fetching

✅ **Better Security**
- Wallets managed by Privy's secure infrastructure
- No wallet-related state in our database

✅ **Easier Maintenance**
- Fewer moving parts
- Wallet changes automatically reflected

✅ **Flexibility**
- Users can manage wallets via Privy dashboard
- Easy to support multiple wallets per user later

### Error Handling

**If user has no wallet:**
```
HTTP 400: No wallet found. Please create an embedded wallet in your Privy account first.
```

**Frontend should:**
1. Catch this error
2. Show user-friendly message
3. Offer "Create Wallet" button
4. Retry after wallet creation

### Testing

**Test Cases:**
1. User with wallet → agent creation succeeds
2. User without wallet → HTTP 400 with clear message
3. Payment check → correctly fetches creator's wallet
4. Multiple agents by same user → same wallet used
5. Wallet deleted in Privy → payment check fails gracefully

### Migration from Old Design

**If you already have `creator_wallet_address` column:**

Option 1: Keep it but don't use it
```sql
-- Column exists but is ignored
-- New agents don't populate it
-- Old agents: fallback to dynamic fetch if null
```

Option 2: Remove it
```sql
ALTER TABLE agents DROP COLUMN IF EXISTS creator_wallet_address;
```

**No migration needed for new installations!**

### Performance Considerations

**Caching Strategy:**
```python
# Cache wallet addresses per request
_wallet_cache = {}

async def get_user_wallet_address(user_id: str) -> Optional[str]:
    if user_id in _wallet_cache:
        return _wallet_cache[user_id]
    
    wallet = await _fetch_wallet_from_privy(user_id)
    _wallet_cache[user_id] = wallet
    return wallet
```

**Note:** Not implemented yet, but can be added if Privy API calls become a bottleneck.

### Privy SDK Limitations

**Python SDK does NOT support:**
- `users.pregenerateWallets()` - Not available
- `wallets.create(owner_id=...)` - Validation error
- Programmatic wallet creation for existing users

**Python SDK DOES support:**
- `users.get(user_id)` - Get user with wallets ✅
- `users.create(..., wallets=[...])` - Create user with wallets ✅
- Reading wallet addresses from linked_accounts ✅

### Next Steps

1. **Frontend: Add Wallet Creation**
   - Add `createWallet()` call on first agent creation
   - Show wallet status in UI
   - Handle wallet creation errors

2. **Backend: Add Caching**
   - Cache wallet addresses per request
   - Reduce Privy API calls

3. **Testing: Full Flow**
   - Test agent creation with wallet
   - Test x402 payment requirements
   - Test error cases

4. **Documentation: User Guide**
   - How to create a wallet
   - Why wallets are required
   - How to view wallet address

## Status

- ✅ Refactored to remove database wallet storage
- ✅ Dynamic wallet fetching implemented
- ✅ x402 payment check updated
- ✅ Agent creation validates wallet existence
- ⏳ Frontend needs wallet creation flow
- ⏳ Testing pending
