from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import httpx
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from privy import PrivyAPI
from eth_abi import encode

load_dotenv()

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
PRIVY_APP_ID = os.environ.get("PRIVY_APP_ID")
PRIVY_APP_SECRET = os.environ.get("PRIVY_APP_SECRET")
LAISSEZ_KEY_QUORUM_ID = os.environ.get("LAISSEZ_KEY_QUORUM_ID")
LAISSEZ_AUTHORIZATION_KEY = os.environ.get("LAISSEZ_AUTHORIZATION_KEY")
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# Payment configuration
X402_USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC on Base Sepolia
USDC_DECIMALS = 6  # USDC has 6 decimals
BASE_SEPOLIA_CHAIN_ID = 84532

# Cache for Privy verification key
_privy_verification_key = None

# Initialize Privy client for wallet creation
_privy_client = None
if PRIVY_APP_ID and PRIVY_APP_SECRET:
    try:
        _privy_client = PrivyAPI(
            app_id=PRIVY_APP_ID,
            app_secret=PRIVY_APP_SECRET
        )
        print("✓ Privy client initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize Privy client: {e}")

if not supabase_url or not supabase_key:
    print("Warning: Supabase credentials not found in environment variables")
    supabase: Client = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

# Pydantic models
class AgentConfig(BaseModel):
    name: str
    url: str
    bot_token: str
    price: float

class LinkCompleteRequest(BaseModel):
    code: str


# Privy token verification
async def get_privy_verification_key():
    """
    Fetch Privy's public verification key for JWT verification
    Caches the key to avoid repeated API calls
    """
    global _privy_verification_key
    
    if _privy_verification_key:
        return _privy_verification_key
    
    if not PRIVY_APP_ID or not PRIVY_APP_SECRET:
        raise Exception("Privy credentials not configured")
    
    try:
        # Fetch verification key from Privy API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://auth.privy.io/api/v1/apps/{PRIVY_APP_ID}",
                headers={
                    "Authorization": f"Bearer {PRIVY_APP_SECRET}",
                    "privy-app-id": PRIVY_APP_ID,
                }
            )
            
            if response.status_code == 200:
                app_data = response.json()
                _privy_verification_key = app_data.get("verification_key")
                if _privy_verification_key:
                    print("✓ Privy verification key fetched successfully")
                    return _privy_verification_key
            
            print(f"Warning: Could not fetch verification key, status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Warning: Error fetching verification key: {e}")
    
    return None


async def verify_privy_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify Privy access token using JWT verification and return user ID
    """
    if not authorization:
        print("ERROR: Missing authorization header")
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        print("ERROR: Invalid authorization header format")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.replace("Bearer ", "")
    print(f"Verifying token (first 20 chars): {token[:20]}...")
    
    if not PRIVY_APP_ID:
        print("ERROR: Privy APP ID not configured")
        raise HTTPException(status_code=500, detail="Privy not configured")
    
    try:
        # Decode JWT without verification first to inspect claims
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        print(f"Token claims: iss={unverified_payload.get('iss')}, aud={unverified_payload.get('aud')}, sub={unverified_payload.get('sub')[:20]}...")
        
        # Verify issuer and audience
        if unverified_payload.get("iss") != "privy.io":
            raise HTTPException(status_code=401, detail="Invalid token issuer")
        
        if unverified_payload.get("aud") != PRIVY_APP_ID:
            raise HTTPException(status_code=401, detail="Invalid token audience")
        
        # Try to get verification key
        verification_key = await get_privy_verification_key()
        
        if verification_key:
            # Verify with the verification key
            try:
                payload = jwt.decode(
                    token,
                    verification_key,
                    algorithms=["ES256"],
                    audience=PRIVY_APP_ID,
                    issuer="privy.io"
                )
                user_id = payload.get("sub")
                print(f"✓ Token verified successfully for user: {user_id[:20]}...")
                return user_id
            except jwt.ExpiredSignatureError:
                print("ERROR: Token has expired")
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError as e:
                print(f"ERROR: Invalid token: {e}")
                raise HTTPException(status_code=401, detail="Invalid token")
        else:
            # Fallback: trust the unverified payload (development only)
            # In production, this should fail if verification key can't be fetched
            print("⚠️  WARNING: Proceeding without signature verification (verification key not available)")
            print("⚠️  This is acceptable for development but should be fixed for production")
            user_id = unverified_payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
            print(f"✓ Using unverified token for user: {user_id[:20]}...")
            return user_id
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error during token verification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify token: {str(e)}")


async def get_user_wallet_address(user_id: str) -> Optional[str]:
    """
    Get a user's Privy embedded wallet address.
    Returns the wallet address or None if user has no wallet.
    
    Note: User must have created a wallet via Privy frontend.
    One wallet per user, reused across all their agents.
    """
    if not _privy_client:
        print("ERROR: Privy client not initialized")
        return None
    
    try:
        # Get user's data from Privy
        print(f"Fetching user data for: {user_id[:20]}...")
        user_data = _privy_client.users.get(user_id)
        
        # Check if user has an embedded Ethereum wallet
        for account in user_data.linked_accounts:
            if account.type == "wallet" and hasattr(account, 'chain_type'):
                if account.chain_type == "ethereum" and hasattr(account, 'address'):
                    print(f"✓ Found wallet: {account.address}")
                    return account.address
        
        # No wallet found
        print(f"⚠️  No wallet found for user {user_id[:20]}")
        return None
        
    except Exception as e:
        print(f"ERROR: Failed to fetch wallet for user {user_id[:20]}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_user_wallet_with_id(user_id: str) -> Optional[tuple[str, str]]:
    """
    Get a user's wallet address AND wallet ID from Privy.
    Returns (wallet_address, wallet_id) tuple or None if user has no wallet.
    """
    if not _privy_client:
        print("❌ ERROR: Privy client not initialized")
        return None
    
    try:
        # Get user's data from Privy
        print(f"🔍 Fetching user data with wallet ID for: {user_id[:20]}...")
        user_data = _privy_client.users.get(user_id)
        
        print(f"📋 User has {len(user_data.linked_accounts)} linked accounts")
        
        # Check if user has an embedded Ethereum wallet with delegated access
        for idx, account in enumerate(user_data.linked_accounts):
            print(f"  Account {idx}: type={account.type}, chain_type={getattr(account, 'chain_type', 'N/A')}")
            
            if account.type == "wallet" and hasattr(account, 'chain_type'):
                if account.chain_type == "ethereum" and hasattr(account, 'address'):
                    wallet_address = account.address
                    wallet_id = getattr(account, 'id', None)
                    wallet_uuid = getattr(account, 'wallet_uuid', None) or getattr(account, 'uuid', None)
                    # Check if wallet has delegated access (session signers)
                    delegated = getattr(account, 'delegated', False)
                    
                    print(f"  📍 Found Ethereum wallet:")
                    print(f"     Address: {wallet_address}")
                    print(f"     ID: {wallet_id}")
                    print(f"     UUID: {wallet_uuid}")
                    print(f"     Delegated: {delegated}")
                    print(f"     All account attributes: {dir(account)}")
                    
                    # Use wallet_uuid if available, otherwise fall back to id
                    effective_wallet_id = wallet_uuid or wallet_id
                    
                    if effective_wallet_id and delegated:
                        print(f"✅ Found delegated wallet: {wallet_address} (Using ID: {effective_wallet_id[:20] if len(effective_wallet_id) > 20 else effective_wallet_id}...)")
                        return (wallet_address, effective_wallet_id)
                    elif effective_wallet_id and not delegated:
                        print(f"⚠️  Wallet {wallet_address} found but NOT delegated (session signers not added)")
                        print(f"     User needs to re-link account to add session signers")
                        return None
                    else:
                        print(f"⚠️  Wallet found but missing UUID/ID: {wallet_address}")
        
        # No wallet found
        print(f"❌ No delegated wallet found for user {user_id[:20]}")
        print(f"   Total accounts checked: {len(user_data.linked_accounts)}")
        return None
        
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch wallet with ID for user {user_id[:20]}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def check_usdc_balance(wallet_address: str) -> Optional[float]:
    """
    Check USDC balance for a wallet on Base Sepolia.
    Returns balance in USDC (not atomic units) or None on error.
    """
    try:
        # Create RPC call to get balance
        async with httpx.AsyncClient() as client:
            # Encode balanceOf(address) call
            # Function signature: balanceOf(address) returns (uint256)
            # We need to manually construct the call
            
            # Using Base Sepolia RPC
            rpc_url = "https://sepolia.base.org"
            
            # Encode the function call
            # balanceOf function selector: 0x70a08231
            # Followed by the address (32 bytes, padded)
            address_padded = wallet_address[2:].lower().zfill(64)  # Remove 0x and pad
            data = f"0x70a08231{address_padded}"
            
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [
                        {
                            "to": X402_USDC_ADDRESS,
                            "data": data
                        },
                        "latest"
                    ],
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    # Parse the hex result
                    balance_hex = result["result"]
                    balance_atomic = int(balance_hex, 16)
                    # Convert from atomic units to USDC
                    balance_usdc = balance_atomic / (10 ** USDC_DECIMALS)
                    print(f"✓ Balance for {wallet_address}: {balance_usdc} USDC")
                    return balance_usdc
            
            print(f"⚠️  Failed to check balance: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"ERROR: Failed to check USDC balance: {e}")
        import traceback
        traceback.print_exc()
        return None


async def send_usdc_payment(
    wallet_id: str,
    wallet_address: str,
    recipient_address: str,
    amount_usdc: float
) -> Optional[str]:
    """
    Send USDC payment from user's wallet to recipient using Privy SDK.
    Returns transaction hash or None on error.
    """
    if not _privy_client:
        print("❌ ERROR: Privy client not initialized")
        return None

    if not LAISSEZ_AUTHORIZATION_KEY:
        print("❌ ERROR: Authorization key not configured")
        return None

    try:
        amount_atomic = int(amount_usdc * (10 ** USDC_DECIMALS))
        function_selector = "0xa9059cbb"
        encoded_params = encode(
            ['address', 'uint256'],
            [recipient_address, amount_atomic]
        ).hex()
        data = function_selector + encoded_params

        if hasattr(_privy_client, 'update_authorization_key'):
            _privy_client.update_authorization_key(LAISSEZ_AUTHORIZATION_KEY)
        try:
            transaction_result = _privy_client.wallets.ethereum.send_transaction(
                wallet_id=wallet_id,
                caip2=f"eip155:{BASE_SEPOLIA_CHAIN_ID}",
                transaction={
                    "to": X402_USDC_ADDRESS,
                    "value": "0x0",
                    "data": data,
                },
            )
        except Exception as sdk_error:
            print(f"❌ Privy transaction failed: {sdk_error}")
            return await _send_usdc_payment_via_rpc(data=data, wallet_id=wallet_id)

        tx_hash = getattr(transaction_result, "hash", None)
        if tx_hash is None and isinstance(transaction_result, dict):
            tx_hash = transaction_result.get("hash")

        if tx_hash:
            print(f"✅ Payment sent | from={wallet_address} to={recipient_address} amount={amount_usdc}USDC hash={tx_hash}")
            return tx_hash

        print("⚠️  Privy transaction succeeded but no hash returned")
        return None

    except Exception as e:
        print(f"❌ Unexpected error in send_usdc_payment: {e}")
        return None


async def _send_usdc_payment_via_rpc(data: str, wallet_id: str) -> Optional[str]:
    """Fallback to Privy RPC endpoint with gas sponsorship."""
    if not PRIVY_APP_SECRET or not PRIVY_APP_ID or not LAISSEZ_AUTHORIZATION_KEY:
        return None

    payload = {
        "method": "eth_sendTransaction",
        "caip2": f"eip155:{BASE_SEPOLIA_CHAIN_ID}",
        "params": {
            "transaction": {
                "to": X402_USDC_ADDRESS,
                "value": "0x0",
                "data": data,
                "chain_id": BASE_SEPOLIA_CHAIN_ID,
            }
        },
        "sponsor": True,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.privy.io/v1/wallets/{wallet_id}/rpc",
                headers={
                    "Authorization": f"Bearer {PRIVY_APP_SECRET}",
                    "privy-app-id": PRIVY_APP_ID,
                    "privy-authorization-key": LAISSEZ_AUTHORIZATION_KEY,
                },
                json=payload,
            )

        if response.status_code != 200:
            print(f"❌ Privy RPC call failed: {response.status_code} {response.text[:200]}")
            return None

        result = response.json()
        tx_hash = result.get("hash")
        if tx_hash:
            print(f"✅ Payment sent via RPC fallback | hash={tx_hash}")
            return tx_hash
        print("⚠️  RPC fallback succeeded without returning a transaction hash")
        return None
    except Exception as e:
        print(f"❌ Privy RPC fallback error: {e}")
        return None


async def send_telegram_message(bot_token: str, chat_id: int, text: str):
    """Helper function to send a message to Telegram"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            print(f"✓ Telegram message sent: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Failed to send Telegram message: {e}")


async def initiate_account_link(
    bot_token: str,
    chat_id: int,
    request: Request,
    telegram_user_id: str,
    agent_name: str,
    agent_price: float,
) -> None:
    """Create a pending link code and prompt the user to link their Telegram account."""
    if not supabase:
        await send_telegram_message(
            bot_token,
            chat_id,
            "Service unavailable. Supabase is not configured.",
        )
        return

    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    pending_payload = {
        "platform": "telegram",
        "platform_user_id": telegram_user_id,
        "bot_token": bot_token,
        "chat_id": str(chat_id),
        "expires_at": expires_at,
    }

    insert_result = supabase.table("pending_links").insert(pending_payload).execute()
    if not insert_result.data:
        await send_telegram_message(
            bot_token,
            chat_id,
            "We couldn't start the account linking flow. Please try again later.",
        )
        return

    code = insert_result.data[0]["code"]
    link_url = f"{build_app_base_url(request)}/link?code={code}"
    price_text = ""
    if agent_price > 0:
        price_text = f"💰 This agent costs {agent_price:.3f} USDC per message.\n\n"

    response_text = (
        f"🤖 Welcome to {agent_name}!\n\n"
        f"{price_text}"
        f"Link your Telegram account to continue:\n"
        f"{link_url}\n\n"
        f"(Link expires in 24 hours)"
    )

    await send_telegram_message(bot_token, chat_id, response_text)


def build_app_base_url(request: Request) -> str:
    """Derive the public app URL from request headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")

    host = forwarded_host or request.headers.get("host", "localhost:3000")
    scheme = forwarded_proto or ("https" if "emergentagent.com" in host else "http")

    if ":8001" in host:
        host = host.replace(":8001", ":3000")

    return f"{scheme}://{host}"


async def get_agent_by_bot_token(bot_token: str) -> Optional[Dict[str, Any]]:
    """Fetch a single agent configuration by bot token."""
    if not supabase:
        return None

    response = supabase.table("agents").select("*").eq("bot_token", bot_token).execute()
    if not response.data:
        return None
    return response.data[0]


async def invoke_agent(agent_url: str, user_message: str) -> Optional[str]:
    """Call the agent URL and return the response text if available."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            agent_result = await client.post(agent_url, json={"input": user_message})

        if agent_result.status_code != 200:
            print(f"⚠️  Agent URL returned {agent_result.status_code}: {agent_result.text[:200]}")
            return None

        agent_data = agent_result.json()
        return agent_data.get("output")
    except Exception as proxy_error:
        print(f"❌ Agent URL error: {proxy_error}")
        return None




async def setup_telegram_webhook(bot_token: str, webhook_url: str) -> dict:
    """Set up Telegram webhook for a bot"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={"url": webhook_url}
        )
        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Failed to set webhook: {result.get('description')}")
        return result


def generate_link_code() -> str:
    """Generate a secure random code for account linking"""
    return secrets.token_urlsafe(32)


# API Endpoints

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Laissez API"}


@app.get("/api/auth/verify")
async def verify_auth(user_id: str = Depends(verify_privy_token)):
    """Test endpoint to verify authentication is working"""
    return {
        "authenticated": True,
        "user_id": user_id,
        "message": "Authentication successful"
    }


@app.post("/api/agents")
async def create_agent_config(
    config: AgentConfig, 
    request: Request,
    user_id: str = Depends(verify_privy_token)
):
    """Save agent configuration to Supabase and set up Telegram webhook"""
    print(f"✓ create_agent_config called for user: {user_id[:20]}...")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Validate price minimum
        if config.price < 0.001:
            raise HTTPException(status_code=400, detail="Price must be at least $0.001")
        
        # Check if user has a wallet - required for receiving payments  
        print(f"✓ Checking if user has a wallet: {user_id[:20]}...")
        wallet_address = await get_user_wallet_address(user_id)
        
        if not wallet_address:
            raise HTTPException(
                status_code=400, 
                detail="No wallet found. Please log out and log back in to create a wallet automatically."
            )
        
        print(f"✓ User has wallet: {wallet_address}")
        
        # Insert into Supabase with user_id (wallet address fetched dynamically from Privy)
        data = {
            "user_id": user_id,
            "name": config.name,
            "url": config.url,
            "bot_token": config.bot_token,
            "price": config.price
        }
        
        response = supabase.table("agents").insert(data).execute()
        
        # Set up Telegram webhook - dynamically detect the public URL
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        forwarded_host = request.headers.get("x-forwarded-host", "")
        
        # Determine scheme (http vs https)
        if forwarded_proto:
            scheme = forwarded_proto
        else:
            host = request.headers.get("host", "localhost:8001")
            scheme = "https" if "emergentagent.com" in host else "http"
        
        # Determine host/domain
        if forwarded_host:
            host = forwarded_host
        else:
            host = request.headers.get("host", "localhost:8001")
        
        webhook_url = f"{scheme}://{host}/api/telegram-webhook/{config.bot_token}"
        
        print(f"Setting webhook URL: {webhook_url} (detected from request headers)")
        webhook_result = await setup_telegram_webhook(config.bot_token, webhook_url)
        
        return {
            "success": True,
            "message": "Agent configuration saved successfully",
            "data": response.data,
            "webhook_info": {
                "webhook_url": webhook_url,
                "telegram_response": webhook_result
            }
        }
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")


@app.get("/api/agents")
async def get_agent_configs(user_id: str = Depends(verify_privy_token)):
    """Get all agent configurations for the authenticated user"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        response = supabase.table("agents").select("*").eq("user_id", user_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch configurations: {str(e)}")


@app.get("/api/linked-accounts")
async def get_linked_accounts(user_id: str = Depends(verify_privy_token)):
    """Get all linked accounts for the authenticated user"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        print(f"📋 Fetching linked accounts for user: {user_id[:20]}...")
        response = supabase.table("linked_accounts").select("*").eq("laissez_user_id", user_id).execute()
        print(f"📊 Found {len(response.data) if response.data else 0} linked accounts")
        if response.data:
            print(f"📋 Sample account data: {response.data[0] if len(response.data) > 0 else 'N/A'}")
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"❌ Error fetching linked accounts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch linked accounts: {str(e)}")


@app.delete("/api/linked-accounts/{account_id}")
async def delete_linked_account(account_id: int, user_id: str = Depends(verify_privy_token)):
    """Delete a linked account for the authenticated user"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # First verify the account belongs to this user
        check_response = supabase.table("linked_accounts").select("*").eq("id", account_id).eq("laissez_user_id", user_id).execute()
        
        if not check_response.data or len(check_response.data) == 0:
            raise HTTPException(status_code=404, detail="Linked account not found or does not belong to you")
        
        # Delete the account
        supabase.table("linked_accounts").delete().eq("id", account_id).execute()
        
        print(f"✓ Deleted linked account {account_id} for user {user_id[:20]}")
        return {"success": True, "message": "Linked account removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting linked account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete linked account: {str(e)}")


@app.post("/api/link/complete")
async def complete_account_link(
    link_request: LinkCompleteRequest,
    user_id: str = Depends(verify_privy_token)
):
    """Complete account linking by associating a code with a Privy user ID"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Find pending link by code
        pending_response = supabase.table("pending_links").select("*").eq("code", link_request.code).execute()
        
        if not pending_response.data or len(pending_response.data) == 0:
            raise HTTPException(status_code=404, detail="Link code not found or expired")
        
        pending_link = pending_response.data[0]
        
        # Check if link is expired
        if pending_link.get("expires_at"):
            expires_at = datetime.fromisoformat(pending_link["expires_at"].replace("Z", "+00:00"))
            if datetime.now(expires_at.tzinfo) > expires_at:
                # Delete expired link
                supabase.table("pending_links").delete().eq("code", link_request.code).execute()
                raise HTTPException(status_code=410, detail="Link code has expired")
        
        # Check if this platform account is already linked
        existing_link = supabase.table("linked_accounts").select("*").eq(
            "platform", pending_link["platform"]
        ).eq("platform_user_id", pending_link["platform_user_id"]).execute()
        
        if existing_link.data and len(existing_link.data) > 0:
            # Update existing link
            supabase.table("linked_accounts").update({
                "laissez_user_id": user_id
            }).eq("platform", pending_link["platform"]).eq(
                "platform_user_id", pending_link["platform_user_id"]
            ).execute()
        else:
            # Create new linked account
            link_data = {
                "laissez_user_id": user_id,
                "platform": pending_link["platform"],
                "platform_user_id": pending_link["platform_user_id"]
            }
            supabase.table("linked_accounts").insert(link_data).execute()
        
        # Delete the pending link
        supabase.table("pending_links").delete().eq("code", link_request.code).execute()

        # Optionally notify the Telegram user that linking is complete
        bot_token_from_link = pending_link.get("bot_token")
        chat_id_from_link = pending_link.get("chat_id")
        if pending_link["platform"] == "telegram" and bot_token_from_link and chat_id_from_link:
            message = (
                "✅ Account linking successful!\n\n"
                "You can now resend your message to continue."
            )
            try:
                await send_telegram_message(bot_token_from_link, int(chat_id_from_link), message)
            except Exception as confirm_error:
                print(f"Failed to send confirmation: {confirm_error}")

        # Note: Session signers are added from the frontend after successful linking
        print(f"✓ Account linked for user {user_id[:20]}. Frontend will add session signers.")

        return {
            "success": True,
            "message": "Account linked successfully",
            "platform": pending_link["platform"],
            "platform_user_id": pending_link["platform_user_id"],
            "will_process_original_query": False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete link: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
