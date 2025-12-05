# Quick Start Guide

## 1. Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Set Up Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your keys:
# - SUPABASE_URL (from Supabase Dashboard → Settings → API)
# - SUPABASE_ANON_KEY (from Supabase Dashboard → Settings → API)
# - SUPABASE_SERVICE_ROLE_KEY (from Supabase Dashboard → Settings → API)
# - OPENAI_API_KEY (from https://platform.openai.com/api-keys)
```

## 3. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Verify It's Working

Open: http://localhost:8000/health

Should return: `{"api":"ok","supabase":true}`

## Required API Keys

| Key | Where to Get |
|-----|--------------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Settings → API → anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API → service_role |
| `OPENAI_API_KEY` | OpenAI Platform → API Keys → Create new secret key |

See `README.md` for detailed instructions.

