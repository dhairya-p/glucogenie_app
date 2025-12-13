"""Quick test script to verify Pinecone setup."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from app.services.rag_service import get_rag_service

# Load environment variables
load_dotenv(backend_dir / ".env")

def test_pinecone_setup():
    """Test Pinecone connection and basic operations."""
    print("=" * 60)
    print("Pinecone Setup Test")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY not found in environment variables")
        print("   Please add it to your .env file:")
        print("   PINECONE_API_KEY=your-api-key-here")
        return False
    else:
        print(f"✅ PINECONE_API_KEY found: {api_key[:10]}...")
    
    # Get RAG service
    rag = get_rag_service()
    
    if not rag.is_available():
        print("❌ RAG service is not available")
        print("   Check your API key and index configuration")
        return False
    
    print(f"✅ RAG service initialized")
    print(f"   Index: {rag.index_name}")
    
    # Test index connection
    try:
        stats = rag.index.describe_index_stats()
        print(f"✅ Index connection successful")
        print(f"   Namespaces: {list(stats.namespaces.keys())}")
        total_vectors = sum(ns.vector_count for ns in stats.namespaces.values())
        print(f"   Total vectors: {total_vectors}")
    except Exception as e:
        print(f"❌ Failed to connect to index: {e}")
        return False
    
    # Test search (if data exists)
    if total_vectors > 0:
        print("\n" + "=" * 60)
        print("Testing Search Functionality")
        print("=" * 60)
        
        test_queries = [
            ("What is Metformin?", "drug"),
            ("What foods are good for diabetes?", "food"),
            ("What is the HbA1c target?", "clinical"),
        ]
        
        for query, index_type in test_queries:
            print(f"\nQuery: '{query}' (type: {index_type})")
            results = rag.search(query, index_type=index_type, top_k=2)
            
            if results:
                print(f"✅ Found {len(results)} results")
                for i, result in enumerate(results, 1):
                    print(f"   [{i}] Score: {result['score']:.3f}")
                    print(f"       Content: {result['content'][:80]}...")
            else:
                print(f"⚠️  No results found (data may not be ingested yet)")
    else:
        print("\n⚠️  No data found in index")
        print("   Run: python scripts/ingest_knowledge.py")
    
    print("\n" + "=" * 60)
    print("✅ Pinecone setup test complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_pinecone_setup()
    sys.exit(0 if success else 1)
