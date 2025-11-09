# Laissez - Deployment Guide

## Preview/Production URL Configuration

Your app is configured to work seamlessly in the Emergent platform's preview and production environments.

### How It Works

**URL Structure:**
- Preview: `https://design-refresh-81.preview.emergentagent.com` (or similar)
- Your domain: `https://design-refresh-81.preview.emergentagent.com`

**Architecture:**
```
Browser Request → https://design-refresh-81.preview.emergentagent.com/api/agents
                                                            ↓
                                        Kubernetes Ingress (routes /api/*)
                                                            ↓
                                        Backend (port 8001)
                                                            ↓
                                        Supabase Database
```

### Key Configuration

**Frontend (`/app/frontend/src/App.js`):**
- Uses **relative URLs**: `fetch('/api/agents')`
- Works automatically in all environments

**package.json:**
- Contains `"proxy": "http://localhost:8001"` for local development
- In production, Kubernetes ingress handles routing

**Backend (`/app/backend/server.py`):**
- All routes prefixed with `/api`
- Listens on `0.0.0.0:8001`
- CORS enabled for all origins

### No Configuration Required! ✓

The app automatically adapts to:
- Local development: `http://localhost:3000` → `http://localhost:8001`
- Preview: `https://design-refresh-81.preview.emergentagent.com` → Same domain `/api/*`
- Production: Same domain routing via Kubernetes ingress

### Testing Your Deployment

1. **Access your preview URL:**
   ```
   https://design-refresh-81.preview.emergentagent.com
   ```

2. **Fill in the form:**
   - Agent URL: Any valid URL
   - Telegram Bot Token: Your bot token
   - Price: Adjust using stepper (min $0.001)

3. **Submit and verify:**
   - Should see "Agent configuration saved successfully!"
   - Form resets to defaults
   - Data persisted to Supabase

### Troubleshooting

**If preview doesn't load:**
1. Check that both frontend and backend services are running
2. Verify Supabase credentials in `/app/backend/.env`
3. Ensure the `agents` table exists in Supabase

**Check backend logs:**
```bash
tail -f /var/log/supervisor/backend.err.log
```

**Check frontend logs:**
```bash
tail -f /var/log/supervisor/frontend.out.log
```

**Verify services:**
```bash
sudo supervisorctl status
```

### Environment Variables

**Backend** (`/app/backend/.env`):
```bash
SUPABASE_URL=https://mhycwrnqmzpkteewrgok.supabase.co
SUPABASE_KEY=eyJhbGc...
MONGO_URL=mongodb://localhost:27017  # Not used but required
```

**Note**: Telegram webhook URL is now **automatically detected** from request headers (no manual configuration needed!)

**Frontend** (`/app/frontend/.env`):
```bash
# Not actively used - app uses relative URLs
# Kept for compatibility
```

### API Endpoints

All endpoints accessible at `https://your-domain/api/`:

- `POST /api/agents` - Create agent configuration
  ```json
  {
    "url": "https://agent.example.com",
    "bot_token": "123456:ABC-DEF",
    "price": 0.005
  }
  ```
  **Note**: This endpoint automatically sets up a Telegram webhook for the bot!

- `GET /api/agents` - Get all configurations
- `GET /api/health` - Health check
- `POST /api/telegram-webhook/{bot_token}` - Telegram webhook endpoint (automatically configured)

### Database Schema

**Supabase Table: `agents`**
```sql
CREATE TABLE agents (
  id SERIAL PRIMARY KEY,
  url TEXT NOT NULL,
  bot_token TEXT NOT NULL,
  price FLOAT NOT NULL DEFAULT 0.001,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Production Checklist

✅ Frontend uses relative URLs (`/api/*`)  
✅ Backend routes prefixed with `/api`  
✅ Backend on port 8001  
✅ CORS configured  
✅ Supabase credentials set  
✅ Database table created  
✅ Services running via supervisor  

## Success!

Your app is production-ready and will work seamlessly at:
`https://design-refresh-81.preview.emergentagent.com`

No additional configuration needed! 🎉
