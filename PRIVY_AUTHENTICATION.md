# Privy Authentication Implementation

## Overview

This application uses Privy for authentication with Google OAuth. Users must authenticate to access the platform and create agents. The system also supports account linking for external platforms like Telegram.

## Authentication Flow

### 1. Main App Access (/)
```
User visits / → RequireAuth checks authentication
  ├─ Not authenticated → Show "Continue with Google" button
  │   └─ User clicks → Privy Google OAuth → Authenticated
  └─ Authenticated → Show AgentConfigPage
```

### 2. Account Linking Flow (/link?code=XXX)
```
External Platform (e.g., Telegram) → User not linked
  ├─ Backend creates pending_link with code
  └─ Sends link to user: /link?code=XXX

User clicks link → LinkAccountPage
  ├─ Code stored in sessionStorage
  ├─ Not authenticated → Prompt Google login
  ├─ After authentication → Call /api/link/complete
  └─ Backend links platform_user_id to Privy user_id
```

## Database Schema

### agents
- `id` (serial, primary key)
- `user_id` (text) - Privy user ID
- `url` (text) - Agent endpoint URL
- `bot_token` (text) - Telegram bot token
- `price` (float) - Price per interaction
- `created_at` (timestamp)

### linked_accounts
- `laissez_user_id` (text) - Privy user ID
- `platform` (varchar) - Platform name (e.g., "telegram")
- `platform_user_id` (varchar) - Platform-specific user ID
- `created_at` (timestamptz)
- **Primary key**: (platform, platform_user_id)

### pending_links
- `code` (uuid, primary key, auto-generated)
- `platform` (varchar) - Platform name
- `platform_user_id` (varchar) - Platform-specific user ID
- `expires_at` (timestamptz) - Link expiration
- `created_at` (timestamptz)

## Backend API Endpoints

### Protected Endpoints (Require Privy Token)

All protected endpoints require `Authorization: Bearer <privy_token>` header.

#### POST /api/agents
Create a new agent configuration.

**Request Body:**
```json
{
  "url": "https://agent-url.com",
  "bot_token": "telegram_bot_token",
  "price": 0.005
}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent configuration saved successfully",
  "data": [...],
  "webhook_info": {
    "webhook_url": "https://...",
    "telegram_response": {...}
  }
}
```

#### GET /api/agents
Get all agent configurations for the authenticated user.

**Response:**
```json
{
  "success": true,
  "data": [...]
}
```

#### POST /api/link/complete
Complete account linking with a code.

**Request Body:**
```json
{
  "code": "pending_link_code"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account linked successfully",
  "platform": "telegram",
  "platform_user_id": "123456789"
}
```

### Public Endpoints

#### GET /api/health
Health check endpoint.

#### POST /api/telegram-webhook/{bot_token}
Receive Telegram webhook updates. Handles:
- Checking if Telegram user is linked
- Creating pending links for unlinked users
- Proxying messages to agent URLs
- LLM fallback for unavailable agents

## Privy Token Verification

The backend verifies Privy tokens using the Privy API:

```python
async def verify_privy_token(authorization: str) -> str:
    # Extract token from "Bearer <token>"
    token = authorization.replace("Bearer ", "")
    
    # Verify with Privy API
    response = await client.get(
        "https://auth.privy.io/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
            "privy-app-id": PRIVY_APP_ID,
        }
    )
    
    # Return user_id
    return response.json().get("id")
```

## Frontend Integration

### PrivyProvider Setup (index.js)
```jsx
<PrivyProvider
  appId={process.env.REACT_APP_PRIVY_APP_ID}
  config={{
    loginMethods: ['google'],
    appearance: { theme: 'dark' },
    embeddedWallets: { createOnLogin: 'off' },
  }}
>
  <App />
</PrivyProvider>
```

### Protected Routes (App.js)
```jsx
function RequireAuth({ children }) {
  const { ready, authenticated, login } = usePrivy();
  
  if (!ready) return <LoadingScreen />;
  if (!authenticated) return <LoginPrompt />;
  return children;
}
```

### Making Authenticated Requests
```jsx
const { getAccessToken } = usePrivy();

const token = await getAccessToken();
const response = await fetch('/api/agents', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
});
```

## Environment Variables

### Backend (.env)
```env
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
PRIVY_APP_ID=cmgax5zki006tl70ci9k2soif
PRIVY_APP_SECRET=4G9dxfCisgxhoGEB...
EMERGENT_LLM_KEY=sk-emergent-...
```

### Frontend (.env)
```env
REACT_APP_PRIVY_APP_ID=cmgax5zki006tl70ci9k2soif
```

## Testing the Implementation

### 1. Test Authentication
1. Visit http://localhost:3000
2. Click "Continue with Google"
3. Complete Google OAuth
4. Should see AgentConfigPage

### 2. Test Agent Creation
1. Fill in agent details (URL, bot token, price)
2. Submit form
3. Check that agent is created with your user_id

### 3. Test Account Linking
1. Create a pending link in database:
```sql
INSERT INTO pending_links (code, platform, platform_user_id, expires_at)
VALUES ('test-code-123', 'telegram', '987654321', NOW() + INTERVAL '24 hours');
```

2. Visit: http://localhost:3000/link?code=test-code-123
3. Authenticate with Google
4. Check that linked_accounts table has new record

### 4. Test Telegram Integration
1. Configure a Telegram bot with webhook
2. Send message to bot as unlinked user
3. Should receive linking URL
4. Complete linking flow
5. Send another message - should work

## Security Considerations

1. **Token Verification**: All protected endpoints verify Privy tokens with Privy API
2. **User Isolation**: Users can only see/manage their own agents
3. **Link Expiration**: Pending links expire after 24 hours
4. **HTTPS Required**: Production should use HTTPS for all communication

## Troubleshooting

### "Missing authorization header"
- Frontend not sending token
- Check: `const token = await getAccessToken()`
- Ensure: `Authorization: Bearer ${token}` header

### "Invalid or expired token"
- Token verification failed with Privy
- User may need to re-authenticate
- Check PRIVY_APP_ID and PRIVY_APP_SECRET

### "Link code not found or expired"
- Code doesn't exist in pending_links table
- Code may have expired (24 hour limit)
- Check expires_at timestamp

### Agents not showing up
- Check that user_id matches between:
  - Privy token user ID
  - agents.user_id in database
- Verify: `GET /api/agents` filters by user_id

## Architecture Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ Privy OAuth
       ↓
┌─────────────────────┐
│  React Frontend     │
│  - PrivyProvider    │
│  - RequireAuth      │
│  - getAccessToken() │
└──────┬──────────────┘
       │ Bearer Token
       ↓
┌─────────────────────┐
│  FastAPI Backend    │
│  - verify_token()   │
│  - Protected Routes │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐      ┌──────────────┐
│  Supabase Database  │←────→│  Privy API   │
│  - agents           │      │  (verify)    │
│  - linked_accounts  │      └──────────────┘
│  - pending_links    │
└─────────────────────┘
```

## Implementation Status

✅ Privy authentication on frontend
✅ Token verification on backend
✅ Protected agent endpoints
✅ User-specific agent filtering
✅ Account linking flow
✅ Telegram integration with linking
✅ Database schema with proper columns
✅ Environment configuration
✅ Error handling and validation

## Next Steps

- [ ] Test with real Telegram bot
- [ ] Add user profile page
- [ ] Add agent management (edit/delete)
- [ ] Add usage analytics per user
- [ ] Add billing integration
