#!/usr/bin/env python3
"""Quick script to test if .env file is loading correctly."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=" * 50)
print("Environment Variables Check")
print("=" * 50)

supabase_url = os.getenv("SUPABASE_URL")
supabase_anon = os.getenv("SUPABASE_ANON_KEY")
supabase_service = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

print(f"\nSUPABASE_URL: {'✅ SET' if supabase_url else '❌ NOT SET'}")
if supabase_url:
    print(f"  Value: {supabase_url[:30]}...")

print(f"\nSUPABASE_ANON_KEY: {'✅ SET' if supabase_anon else '❌ NOT SET'}")
if supabase_anon:
    print(f"  Value: {supabase_anon[:30]}...")

print(f"\nSUPABASE_SERVICE_ROLE_KEY: {'✅ SET' if supabase_service else '❌ NOT SET'}")
if supabase_service:
    print(f"  Value: {supabase_service[:30]}...")

print(f"\nOPENAI_API_KEY: {'✅ SET' if openai_key else '❌ NOT SET'}")
if openai_key:
    print(f"  Value: {openai_key[:10]}...")

print("\n" + "=" * 50)

# Try to create a Supabase client
if supabase_url and (supabase_anon or supabase_service):
    try:
        from supabase import create_client
        
        key = supabase_service or supabase_anon
        client = create_client(supabase_url, key)
        
        # Test connection
        settings = client.auth.get_settings()
        print("\n✅ Supabase connection test: SUCCESS")
        print(f"   Auth settings retrieved successfully")
    except Exception as e:
        print(f"\n❌ Supabase connection test: FAILED")
        print(f"   Error: {e}")
else:
    print("\n⚠️  Cannot test Supabase connection - missing credentials")

