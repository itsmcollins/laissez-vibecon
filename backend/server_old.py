from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import httpx

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

# Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Warning: Supabase credentials not found in environment variables")
    supabase: Client = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

class AgentConfig(BaseModel):
    url: str
    bot_token: str
    price: float


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Laissez API"}

@app.post("/api/agents")
async def create_agent_config(config: AgentConfig, request: Request):
    """Save agent configuration to Supabase and set up Telegram webhook"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Validate price minimum
        if config.price < 0.001:
            raise HTTPException(status_code=400, detail="Price must be at least $0.001")
        
        # Insert into Supabase
        data = {
            "url": config.url,
            "bot_token": config.bot_token,
            "price": config.price
        }
        
        response = supabase.table("agents").insert(data).execute()
        
        # Set up Telegram webhook - dynamically detect the public URL
        # Check for proxy headers first (set by Kubernetes ingress / load balancer)
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        forwarded_host = request.headers.get("x-forwarded-host", "")
        
        # Determine scheme (http vs https)
        if forwarded_proto:
            scheme = forwarded_proto
        else:
            # Assume https for emergentagent.com domains, http for localhost
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
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")

@app.get("/api/agents")
async def get_agent_configs():
    """Get all agent configurations"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        response = supabase.table("agents").select("*").execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch configurations: {str(e)}")


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


@app.post("/api/telegram-webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    """
    Receive updates from Telegram and proxy to configured agent URL.
    Falls back to LLM if agent URL fails.
    """
    try:
        # Parse the incoming update from Telegram
        update_data = await request.json()
        
        # Check if there's a message with text
        if "message" in update_data and "text" in update_data["message"]:
            chat_id = update_data["message"]["chat"]["id"]
            user_message = update_data["message"]["text"]
            
            # Get agent configuration from Supabase
            if not supabase:
                response_text = await get_llm_fallback_response(user_message)
            else:
                try:
                    # Query for agent by bot_token
                    agent_response = supabase.table("agents").select("*").eq("bot_token", bot_token).execute()
                    
                    if agent_response.data and len(agent_response.data) > 0:
                        agent_url = agent_response.data[0]["url"]
                        
                        # Try to proxy to agent URL
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                agent_result = await client.post(
                                    agent_url,
                                    json={"input": user_message}
                                )
                                
                                # Check if response is successful and has output field
                                if agent_result.status_code == 200:
                                    agent_data = agent_result.json()
                                    if "output" in agent_data:
                                        response_text = agent_data["output"]
                                    else:
                                        # Malformed response, use LLM fallback
                                        print(f"Agent response missing 'output' field: {agent_data}")
                                        response_text = await get_llm_fallback_response(user_message)
                                else:
                                    # Agent URL returned error
                                    print(f"Agent URL returned {agent_result.status_code}: {agent_result.text[:200]}")
                                    response_text = await get_llm_fallback_response(user_message)
                        except Exception as proxy_error:
                            # Agent URL failed (timeout, connection error, etc.)
                            print(f"Agent URL proxy error: {proxy_error}")
                            response_text = await get_llm_fallback_response(user_message)
                    else:
                        # Bot token not found in database
                        response_text = "Configuration not found. Please set up your agent first."
                except Exception as db_error:
                    print(f"Database error: {db_error}")
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