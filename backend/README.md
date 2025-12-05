# Backend Setup Guide

## Prerequisites

- **Python 3.11+** (as per cursorrules requirement)
- **pip** (Python package manager)
- **Virtual environment** (recommended)

## Step 1: Install Python Dependencies

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

4. **Install all dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Step 2: Required API Keys & Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

### Required (Critical)

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# OpenAI API Key (for LangChain chat model)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Optional (for future Neo4j GraphRAG features)

```bash
# Neo4j Configuration (optional - not currently used but defined in Settings)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

## Step 3: Where to Get API Keys

### Supabase Keys

1. Go to [https://supabase.com](https://supabase.com) and sign in
2. Select your project (or create a new one)
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_ANON_KEY`
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` ⚠️ **Keep this secret!**

### OpenAI API Key

1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy the key → `OPENAI_API_KEY` ⚠️ **Keep this secret!**

**Note:** You'll need a paid OpenAI account or credits to use the API. The code uses `gpt-4o-mini` which is cost-effective.

## Step 4: Verify Your .env File

Your `backend/.env` should look like this:

```bash
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-proj-...
```

**⚠️ Important:** 
- Never commit `.env` to git (it should be in `.gitignore`)
- The `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security - keep it secure
- The `OPENAI_API_KEY` gives access to your OpenAI account - keep it secure

## Step 5: Run the Backend

### Development Mode (with auto-reload)

```bash
# Make sure you're in the backend directory
cd backend

# Activate virtual environment (if not already active)
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate    # Windows

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server will start at: **http://localhost:8000**

## Step 6: Verify Backend is Running

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```
   
   Expected response:
   ```json
   {"api":"ok","supabase":true}
   ```

2. **API Documentation:**
   - Open in browser: **http://localhost:8000/docs**
   - Interactive Swagger UI for testing endpoints

3. **Alternative Docs:**
   - ReDoc: **http://localhost:8000/redoc**

## Troubleshooting

### Issue: `ModuleNotFoundError`

**Solution:** Make sure you've activated your virtual environment and installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: `RuntimeError: Supabase URL or key not configured`

**Solution:** 
- Check that `.env` file exists in `backend/` directory
- Verify all required environment variables are set
- Restart the server after creating/updating `.env`

### Issue: `401 Unauthorized` when calling `/chat_stream`

**Solution:**
- Ensure the Flutter app is sending a valid Supabase JWT token
- Check that `SUPABASE_ANON_KEY` matches your Supabase project
- Verify the user is authenticated in Supabase

### Issue: `OpenAI API error` or `Rate limit exceeded`

**Solution:**
- Verify `OPENAI_API_KEY` is correct
- Check your OpenAI account has credits/quota
- Consider using a different model if needed (edit `chat_graph.py`)

### Issue: Port 8000 already in use

**Solution:** Use a different port:
```bash
uvicorn app.main:app --reload --port 8001
```
Then update Flutter `chat_provider.dart` to use the new port.

## Project Structure

```
backend/
├── app/
│   ├── agents/          # Agent implementations (Router, Lifestyle, Clinical, Cultural)
│   ├── core/            # Core chat graph logic
│   ├── routers/         # FastAPI route modules (future)
│   ├── schemas/         # Pydantic models (PatientContext, etc.)
│   └── main.py          # FastAPI app entry point
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md           # This file
```

## Next Steps

Once the backend is running:

1. **Test the health endpoint:** `curl http://localhost:8000/health`
2. **Test chat streaming:** Use the Flutter app or Postman to call `/chat_stream`
3. **Check logs:** The server will show request logs in the terminal
4. **Monitor Supabase:** Verify data is being fetched correctly from your Supabase tables

## Environment Variables Summary

| Variable | Required | Description | Where to Get |
|----------|----------|-------------|--------------|
| `SUPABASE_URL` | ✅ Yes | Your Supabase project URL | Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | ✅ Yes | Public anon key | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ Yes | Service role key (bypasses RLS) | Supabase Dashboard → Settings → API |
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for LLM | OpenAI Platform → API Keys |
| `NEO4J_URI` | ❌ Optional | Neo4j connection URI | Your Neo4j instance |
| `NEO4J_USERNAME` | ❌ Optional | Neo4j username | Your Neo4j instance |
| `NEO4J_PASSWORD` | ❌ Optional | Neo4j password | Your Neo4j instance |

