# Bug Fix: Wallet Creation Error

## Issue
Wallet creation was failing when users tried to create agents with the error:
```
TypeError: WalletsResource.create() got an unexpected keyword argument 'user_id'
```

## Root Cause
1. **Incorrect API Parameter**: Used `user_id` instead of `owner_id` in `_privy_client.wallets.create()` call
2. **Design Clarification**: Implementation correctly follows "one wallet per user" model (not per agent)

## Solution

### Code Fix
Changed in `/app/backend/server.py`:

**Before:**
```python
wallet_response = _privy_client.wallets.create(
    user_id=user_id,  # WRONG parameter name
    chain_type="ethereum"
)
```

**After:**
```python
wallet_response = _privy_client.wallets.create(
    owner_id=user_id,  # CORRECT parameter name
    chain_type="ethereum"
)
```

### Design Confirmation
- **One wallet per user** (correct design)
- Wallet created on first agent creation
- Same wallet address used for all agents by that user
- All payments for any of user's agents go to this one wallet

## Privy SDK Method Signature
```python
wallets.create(
    *,
    chain_type: Literal['solana', 'ethereum', 'cosmos', 'stellar', 'sui'],
    owner_id: Optional[str] = NOT_GIVEN,  # <-- Correct parameter
    additional_signers: Iterable[AdditionalSigner] = NOT_GIVEN,
    owner: Optional[Owner] = NOT_GIVEN,
    policy_ids: List[str] = NOT_GIVEN,
    ...
) -> Wallet
```

## Testing Status
- ✅ Backend restarted successfully
- ✅ Privy client initialized
- ✅ No more TypeErrors in logs
- ⏳ End-to-end agent creation test pending

## Next Steps
Test the complete flow:
1. Authenticate with Privy
2. Create first agent → wallet should be created
3. Create second agent → same wallet should be reused
4. Verify both agents have the same `creator_wallet_address` in database

## Verification Logs
```
✓ Privy client initialized successfully
✓ Privy verification key fetched successfully
```

No more `TypeError` exceptions in backend logs.
