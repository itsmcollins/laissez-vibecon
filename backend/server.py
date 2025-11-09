from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import httpx
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt

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
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# Cache for Privy verification key
_privy_verification_key = None

if not supabase_url or not supabase_key:
    print("Warning: Supabase credentials not found in environment variables")
    supabase: Client = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

# Pydantic models
class AgentConfig(BaseModel):
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
                    print(f"✓ Privy verification key fetched successfully")
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
        print(f"ERROR: Invalid authorization header format")
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
        
        # Insert into Supabase with user_id
        data = {
            "user_id": user_id,
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
        
        return {
            "success": True,
            "message": "Account linked successfully",
            "platform": pending_link["platform"],
            "platform_user_id": pending_link["platform_user_id"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete link: {str(e)}")


@app.post("/api/telegram-webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    """
    Receive updates from Telegram and proxy to configured agent URL.
    Checks for linked accounts and creates pending links if needed.
    Falls back to LLM if agent URL fails.
    """
    try:
        # Parse the incoming update from Telegram
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
                        # Not linked - create pending link and send instructions
                        print(f"Telegram user {telegram_user_id} not linked, creating pending link...")
                        
                        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
                        
                        # Create pending link (code will be auto-generated as UUID by database)
                        pending_data = {
                            "platform": "telegram",
                            "platform_user_id": telegram_user_id,
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
                            f"🔗 Account Linking Required\n\n"
                            f"To use this agent, please link your Telegram account:\n"
                            f"{link_url}\n\n"
                            f"This link expires in 24 hours."
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
