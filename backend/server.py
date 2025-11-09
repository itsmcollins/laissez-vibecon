from fastapi import FastAPI, HTTPException, Request, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from viem import encodeFunctionData, erc20Abi

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

# x402 Configuration
X402_FACILITATOR_URL = "https://x402.org/facilitator"
X402_NETWORK = "base-sepolia"
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
        print("ERROR: Privy client not initialized")
        return None
    
    try:
        # Get user's data from Privy
        print(f"Fetching user data with wallet ID for: {user_id[:20]}...")
        user_data = _privy_client.users.get(user_id)
        
        # Check if user has an embedded Ethereum wallet with delegated access
        for account in user_data.linked_accounts:
            if account.type == "wallet" and hasattr(account, 'chain_type'):
                if account.chain_type == "ethereum" and hasattr(account, 'address'):
                    wallet_address = account.address
                    wallet_id = getattr(account, 'id', None)
                    # Check if wallet has delegated access (session signers)
                    delegated = getattr(account, 'delegated', False)
                    
                    if wallet_id and delegated:
                        print(f"✓ Found delegated wallet: {wallet_address} (ID: {wallet_id[:20]}...)")
                        return (wallet_address, wallet_id)
                    elif wallet_id and not delegated:
                        print(f"⚠️  Wallet {wallet_address} found but not delegated")
                        return None
        
        # No wallet found
        print(f"⚠️  No delegated wallet found for user {user_id[:20]}")
        return None
        
    except Exception as e:
        print(f"ERROR: Failed to fetch wallet with ID for user {user_id[:20]}: {e}")
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


async def add_session_signers(wallet_address: str, wallet_id: str) -> bool:
    """
    Add session signers (server-side delegation) to a user's wallet using Privy API.
    Returns True if successful, False otherwise.
    """
    if not LAISSEZ_KEY_QUORUM_ID or not LAISSEZ_AUTHORIZATION_KEY:
        print("ERROR: Session signer credentials not configured")
        return False
    
    try:
        print(f"Adding session signers to wallet {wallet_address}...")
        
        # Use Privy API to add session signers
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.privy.io/v1/wallets/{wallet_id}/session_signers",
                headers={
                    "Authorization": f"Bearer {PRIVY_APP_SECRET}",
                    "privy-app-id": PRIVY_APP_ID,
                },
                json={
                    "signers": [
                        {
                            "signer_id": LAISSEZ_KEY_QUORUM_ID,
                            "policy_ids": []  # No policies - unrestricted access
                        }
                    ]
                }
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Session signers added successfully to {wallet_address}")
                return True
            else:
                print(f"⚠️  Failed to add session signers: {response.status_code} - {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"ERROR: Failed to add session signers: {e}")
        import traceback
        traceback.print_exc()
        return False


async def send_usdc_payment(
    wallet_id: str,
    wallet_address: str,
    recipient_address: str,
    amount_usdc: float
) -> Optional[str]:
    """
    Send USDC payment from user's wallet to recipient using Privy server-side signing.
    Returns transaction hash or None on error.
    """
    if not LAISSEZ_AUTHORIZATION_KEY:
        print("ERROR: Authorization key not configured")
        return None
    
    try:
        print(f"Sending {amount_usdc} USDC from {wallet_address} to {recipient_address}...")
        
        # Convert USDC amount to atomic units
        amount_atomic = int(amount_usdc * (10 ** USDC_DECIMALS))
        
        # Encode transfer function call using viem
        data = encodeFunctionData(
            abi=erc20Abi,
            functionName="transfer",
            args=[recipient_address, amount_atomic]
        )
        
        # Use Privy's server-side signing API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.privy.io/v1/wallets/{wallet_id}/rpc",
                headers={
                    "Authorization": f"Bearer {PRIVY_APP_SECRET}",
                    "privy-app-id": PRIVY_APP_ID,
                },
                json={
                    "method": "eth_sendTransaction",
                    "params": {
                        "caip2": f"eip155:{BASE_SEPOLIA_CHAIN_ID}",
                        "params": {
                            "transaction": {
                                "to": X402_USDC_ADDRESS,
                                "value": "0x0",
                                "data": data,
                                "chain_id": BASE_SEPOLIA_CHAIN_ID
                            }
                        },
                        "sponsor": True,  # Enable gas sponsorship
                        "authorization_context": {
                            "authorization_private_keys": [LAISSEZ_AUTHORIZATION_KEY]
                        }
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                tx_hash = result.get("hash")
                if tx_hash:
                    print(f"✓ Transaction sent: {tx_hash}")
                    return tx_hash
            
            print(f"⚠️  Transaction failed: {response.status_code} - {response.text[:300]}")
            return None
            
    except Exception as e:
        print(f"ERROR: Failed to send USDC payment: {e}")
        import traceback
        traceback.print_exc()
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


async def process_original_telegram_query(telegram_user_id: str, original_query: str, laissez_user_id: str, bot_token: str, chat_id: int):
    """
    Process the original query that triggered account linking.
    Sends the agent's response back to the user on Telegram.
    """
    try:
        print(f"Processing original query for Telegram user {telegram_user_id}...")
        
        # Get agent configuration
        agent_response = supabase.table("agents").select("*").eq("bot_token", bot_token).execute()
        
        if not agent_response.data or len(agent_response.data) == 0:
            print("No agent found for bot_token")
            return
        
        agent_url = agent_response.data[0]["url"]
        print(f"Proxying to agent URL: {agent_url}")
        
        # Try to proxy to agent URL
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                agent_result = await client.post(
                    agent_url,
                    json={"input": original_query}
                )
                
                if agent_result.status_code == 200:
                    agent_data = agent_result.json()
                    if "output" in agent_data:
                        response_text = agent_data["output"]
                    else:
                        print(f"Agent response missing 'output' field: {agent_data}")
                        response_text = await get_llm_fallback_response(original_query)
                else:
                    print(f"Agent URL returned {agent_result.status_code}")
                    response_text = await get_llm_fallback_response(original_query)
        except Exception as proxy_error:
            print(f"Agent URL proxy error: {proxy_error}")
            response_text = await get_llm_fallback_response(original_query)
        
        # Send response to Telegram
        print(f"Sending response to Telegram chat {chat_id}...")
        async with httpx.AsyncClient() as client:
            telegram_response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": response_text
                }
            )
            print(f"✓ Telegram API response: {telegram_response.status_code}")
            
    except Exception as e:
        print(f"Error processing original query: {e}")
        import traceback
        traceback.print_exc()


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


async def get_llm_fallback_response(user_message: str) -> str:
    """Generate fallback response using LLM when agent URL fails"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return "I apologize, but I'm unable to connect to your configured agent at the moment. Please try again later."
    
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=api_key,
            session_id="telegram-fallback",
            system_message=f"""You are a helpful assistant filling in for an unavailable agent. 
The user asked: '{user_message}'

Unfortunately, their configured agent is currently unavailable or experiencing issues. 
Please provide the most helpful and accurate response you can to their query, while politely acknowledging that you're a backup assistant and their primary agent couldn't be reached.

Be concise, helpful, and empathetic about the service disruption."""
        ).with_model("openai", "gpt-5-mini")
        
        # Send message and get response
        response = await chat.send_message(UserMessage(text=user_message))
        return response
    except Exception as e:
        print(f"LLM fallback error: {e}")
        return "I apologize, but I'm unable to process your request at the moment. Please try again later."


def generate_link_code() -> str:
    """Generate a secure random code for account linking"""
    return secrets.token_urlsafe(32)


async def check_x402_payment(request: Request, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Check if x402 payment is required and valid for a telegram webhook request.
    Returns None if payment is valid, or a dict with 402 response if payment is required.
    
    Fetches creator wallet address dynamically from Privy using agent's user_id.
    """
    if not supabase:
        return None
    
    try:
        # Get agent configuration by bot_token
        agent_response = supabase.table("agents").select("*").eq("bot_token", bot_token).execute()
        
        if not agent_response.data or len(agent_response.data) == 0:
            # No agent found, don't require payment
            return None
        
        agent = agent_response.data[0]
        price = agent.get("price", 0)
        creator_user_id = agent.get("user_id")
        
        # If no price or no user_id, don't require payment
        if not price or price <= 0 or not creator_user_id:
            return None
        
        # Fetch creator's wallet address from Privy dynamically
        creator_wallet = await get_user_wallet_address(creator_user_id)
        
        if not creator_wallet:
            print(f"WARNING: Could not fetch wallet for user {creator_user_id[:20]}, skipping payment")
            return None
        
        # Check for X-PAYMENT header
        x_payment_header = request.headers.get("X-PAYMENT") or request.headers.get("x-payment")
        
        if not x_payment_header:
            # No payment provided, return 402 with payment requirements
            price_atomic = int(price * 1_000_000)  # Convert to USDC atomic units (6 decimals)
            
            return {
                "status_code": 402,
                "body": {
                    "x402Version": 1,
                    "accepts": [{
                        "scheme": "exact",
                        "network": X402_NETWORK,
                        "maxAmountRequired": str(price_atomic),
                        "resource": str(request.url.path),
                        "description": f"Payment required to message this agent (${price})",
                        "payTo": creator_wallet,
                        "asset": X402_USDC_ADDRESS,
                        "maxTimeoutSeconds": 60
                    }],
                    "error": "Payment required"
                }
            }
        
        # Payment header exists - in a full implementation, we would verify it with the facilitator
        # For now, we'll trust the payment header (in production, verify with facilitator)
        print(f"✓ X-PAYMENT header present for bot {bot_token[:20]}")
        return None
        
    except Exception as e:
        print(f"Error checking x402 payment: {e}")
        import traceback
        traceback.print_exc()
        # On error, allow request to proceed without payment
        return None


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


@app.post("/api/link/complete")
async def complete_account_link(
    link_request: LinkCompleteRequest,
    background_tasks: BackgroundTasks,
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
        
        # Get original query if it exists
        original_query = pending_link.get("original_query")
        bot_token_from_link = pending_link.get("bot_token")
        chat_id_from_link = pending_link.get("chat_id")
        
        # Delete the pending link
        supabase.table("pending_links").delete().eq("code", link_request.code).execute()
        
        # If there was an original query, send confirmation and schedule processing in background
        # This allows the frontend to complete the auth flow immediately
        if original_query and pending_link["platform"] == "telegram" and bot_token_from_link and chat_id_from_link:
            print(f"Sending confirmation message to Telegram...")
            
            # Send immediate confirmation to user in Telegram
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token_from_link}/sendMessage",
                        json={
                            "chat_id": int(chat_id_from_link),
                            "text": "✅ Account linking successful! Now returning to your original message..."
                        }
                    )
                    print(f"✓ Confirmation sent to Telegram")
            except Exception as confirm_error:
                print(f"Failed to send confirmation: {confirm_error}")
            
            # Schedule the original query to be processed in background
            print(f"Scheduling background processing of original query: {original_query[:50]}...")
            background_tasks.add_task(
                process_original_telegram_query,
                telegram_user_id=pending_link["platform_user_id"],
                original_query=original_query,
                laissez_user_id=user_id,
                bot_token=bot_token_from_link,
                chat_id=int(chat_id_from_link)
            )
        
        # Return success immediately - original query will be processed in background
        return {
            "success": True,
            "message": "Account linked successfully",
            "platform": pending_link["platform"],
            "platform_user_id": pending_link["platform_user_id"],
            "will_process_original_query": bool(original_query and bot_token_from_link and chat_id_from_link)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete link: {str(e)}")


@app.post("/api/telegram-webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    """
    Receive updates from Telegram and handle account linking + payments.
    
    Flow:
    1. Check if Telegram user is linked to Laissez account
    2. If not linked: Send message with price and account creation link
    3. If linked: Handle payment and proxy to agent (future: we pay on their behalf)
    """
    try:
        # Parse the incoming update from Telegram - ALWAYS accept it
        update_data = await request.json()
        print(f"\n{'='*60}")
        print(f"Telegram webhook received for bot token: {bot_token[:20]}...")
        
        # Check if there's a message with text
        if "message" in update_data and "text" in update_data["message"]:
            chat_id = update_data["message"]["chat"]["id"]
            user_message = update_data["message"]["text"]
            telegram_user_id = str(update_data["message"]["from"]["id"])
            
            print(f"Message from Telegram user {telegram_user_id}: {user_message[:50]}...")
            print(f"Chat ID: {chat_id}")
            
            # Check if telegram account is linked
            if supabase:
                try:
                    linked_account = supabase.table("linked_accounts").select("*").eq(
                        "platform", "telegram"
                    ).eq("platform_user_id", telegram_user_id).execute()
                    
                    if not linked_account.data or len(linked_account.data) == 0:
                        # Not linked - create pending link and show price
                        print(f"Telegram user {telegram_user_id} not linked, creating pending link...")
                        
                        # Get agent configuration to show name and price in message
                        agent_response = supabase.table("agents").select("name, price").eq(
                            "bot_token", bot_token
                        ).execute()
                        
                        agent_name = "this Agent"
                        price_display = ""
                        if agent_response.data and len(agent_response.data) > 0:
                            agent_data = agent_response.data[0]
                            # Get agent name
                            if agent_data.get("name"):
                                agent_name = agent_data["name"]
                            # Get price
                            price = agent_data.get("price", 0)
                            if price and price > 0:
                                price_display = f"💰 This agent costs ${price:.3f} per message to use.\n\n"
                        
                        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
                        
                        # Create pending link (code will be auto-generated as UUID by database)
                        # Store the original query, bot_token, and chat_id so we can process it after linking
                        pending_data = {
                            "platform": "telegram",
                            "platform_user_id": telegram_user_id,
                            "original_query": user_message,  # Store the user's original message
                            "bot_token": bot_token,  # Store which bot/agent they're messaging
                            "chat_id": str(chat_id),  # Store where to send the response
                            "expires_at": expires_at
                        }
                        
                        insert_result = supabase.table("pending_links").insert(pending_data).execute()
                        
                        # Get the generated code from the inserted record
                        if insert_result.data and len(insert_result.data) > 0:
                            code = insert_result.data[0]["code"]
                            print(f"✓ Pending link created with code: {code}")
                        else:
                            raise Exception("Failed to create pending link")
                        
                        # Construct the frontend URL using the same domain as the webhook request
                        # The webhook is received at: {scheme}://{host}/api/telegram-webhook/{token}
                        # We need to link to:        {scheme}://{host}/link?code={code}
                        forwarded_proto = request.headers.get("x-forwarded-proto")
                        forwarded_host = request.headers.get("x-forwarded-host")
                        
                        # Determine scheme
                        if forwarded_proto:
                            scheme = forwarded_proto
                        else:
                            # Check if running on emergentagent.com or similar production domain
                            host = request.headers.get("host", "")
                            scheme = "https" if ("emergentagent.com" in host or not host.startswith("localhost")) else "http"
                        
                        # Determine host
                        if forwarded_host:
                            host = forwarded_host
                        else:
                            host = request.headers.get("host", "localhost:3000")
                            # Remove port if it's the backend port (8001), as frontend is on same domain
                            if ":8001" in host:
                                host = host.replace(":8001", ":3000")
                        
                        app_url = f"{scheme}://{host}"
                        link_url = f"{app_url}/link?code={code}"
                        print(f"✓ Constructed link URL: {link_url}")
                        
                        response_text = (
                            f"🤖 Welcome to {agent_name}!\n\n"
                            f"{price_display}"
                            f"Start using it with your Laissez account:\n"
                            f"{link_url}\n\n"
                            f"(Link expires in 24 hours)"
                        )
                        
                        # Send reply to Telegram
                        print(f"Sending linking message to Telegram chat {chat_id}...")
                        async with httpx.AsyncClient() as client:
                            telegram_response = await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": response_text
                                }
                            )
                            print(f"✓ Telegram API response: {telegram_response.status_code}")
                        
                        return {"ok": True}
                    
                    # Account is linked - get laissez_user_id (Privy user ID)
                    laissez_user_id = linked_account.data[0]["laissez_user_id"]
                    print(f"✓ Telegram user {telegram_user_id} linked to Privy user {laissez_user_id[:20]}...")
                    
                    # Get agent configuration by bot_token (NOT filtered by user_id)
                    # Any authenticated user can message any agent
                    agent_response = supabase.table("agents").select("*").eq(
                        "bot_token", bot_token
                    ).execute()
                    
                    print(f"Found {len(agent_response.data) if agent_response.data else 0} agents for bot token")
                    
                    if agent_response.data and len(agent_response.data) > 0:
                        agent_url = agent_response.data[0]["url"]
                        
                        # Try to proxy to agent URL
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                agent_result = await client.post(
                                    agent_url,
                                    json={"input": user_message}
                                )
                                
                                if agent_result.status_code == 200:
                                    agent_data = agent_result.json()
                                    if "output" in agent_data:
                                        response_text = agent_data["output"]
                                    else:
                                        print(f"Agent response missing 'output' field: {agent_data}")
                                        response_text = await get_llm_fallback_response(user_message)
                                else:
                                    print(f"Agent URL returned {agent_result.status_code}: {agent_result.text[:200]}")
                                    response_text = await get_llm_fallback_response(user_message)
                        except Exception as proxy_error:
                            print(f"Agent URL proxy error: {proxy_error}")
                            response_text = await get_llm_fallback_response(user_message)
                    else:
                        response_text = "Agent configuration not found. Please set up your agent first."
                
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    response_text = await get_llm_fallback_response(user_message)
            else:
                response_text = await get_llm_fallback_response(user_message)
            
            # Send reply to Telegram
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": response_text
                    }
                )
        
        # Always return 200 OK to Telegram
        return {"ok": True}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Return 200 anyway to avoid Telegram retrying
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
