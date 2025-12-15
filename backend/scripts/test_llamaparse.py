"""Quick test script to validate LlamaParse setup and functionality.

Run this before full ingestion to ensure everything works.

Usage:
    python scripts/test_llamaparse.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required packages are installed."""
    logger.info("Testing imports...")

    try:
        from llama_parse import LlamaParse
        logger.info("  ✓ llama-parse")
    except ImportError:
        logger.error("  ❌ llama-parse not installed")
        logger.error("     Install: pip install llama-parse")
        return False

    try:
        from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
        logger.info("  ✓ llama-index-core")
    except ImportError:
        logger.error("  ❌ llama-index-core not installed")
        logger.error("     Install: pip install llama-index-core")
        return False

    try:
        from llama_index.core.node_parser import HierarchicalNodeParser
        logger.info("  ✓ HierarchicalNodeParser")
    except ImportError:
        logger.error("  ❌ HierarchicalNodeParser not available")
        return False

    try:
        from llama_index.embeddings.openai import OpenAIEmbedding
        logger.info("  ✓ llama-index-embeddings-openai")
    except ImportError:
        logger.error("  ❌ llama-index-embeddings-openai not installed")
        logger.error("     Install: pip install llama-index-embeddings-openai")
        return False

    try:
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        logger.info("  ✓ llama-index-vector-stores-pinecone")
    except ImportError:
        logger.error("  ❌ llama-index-vector-stores-pinecone not installed")
        logger.error("     Install: pip install llama-index-vector-stores-pinecone")
        return False

    try:
        from pinecone import Pinecone
        logger.info("  ✓ pinecone")
    except ImportError:
        logger.error("  ❌ pinecone not installed")
        logger.error("     Install: pip install pinecone")
        return False

    logger.info("✓ All imports successful\n")
    return True


def test_environment():
    """Test environment variables."""
    logger.info("Testing environment variables...")

    required = {
        "LLAMA_CLOUD_API_KEY": "Get from cloud.llamaindex.ai",
        "PINECONE_API_KEY": "Pinecone API key",
        "OPENAI_API_KEY": "OpenAI API key",
    }

    all_present = True
    for var, description in required.items():
        value = os.getenv(var)
        if value:
            logger.info(f"  ✓ {var}: {'*' * 8}{value[-4:]}")
        else:
            logger.error(f"  ❌ {var} not set ({description})")
            all_present = False

    if all_present:
        logger.info("✓ All environment variables set\n")
    else:
        logger.error("\n⚠️  Add missing variables to backend/.env\n")

    return all_present


def test_llamaparse_parser():
    """Test LlamaParse parser initialization."""
    logger.info("Testing LlamaParse parser...")

    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        logger.error("  ❌ LLAMA_CLOUD_API_KEY not set, skipping parser test")
        return False

    try:
        from llama_parse import LlamaParse

        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            verbose=False,
        )

        logger.info("  ✓ LlamaParse parser initialized")
        logger.info(f"     - Result type: markdown")
        logger.info(f"     - API key: ***{api_key[-4:]}")
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize LlamaParse: {e}")
        return False


def test_pdf_parsing():
    """Test parsing a sample PDF."""
    logger.info("Testing PDF parsing...")

    rag_docs_dir = backend_dir / "rag_docs" / "clinical_safety_docs"
    if not rag_docs_dir.exists():
        logger.warning(f"  ⚠️  Directory not found: {rag_docs_dir}")
        logger.warning("     Skipping PDF parsing test")
        return True  # Not a failure, just skip

    pdf_files = list(rag_docs_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("  ⚠️  No PDF files found")
        return True

    # Test on smallest PDF
    test_pdf = min(pdf_files, key=lambda p: p.stat().st_size)
    logger.info(f"  Testing with: {test_pdf.name} ({test_pdf.stat().st_size / 1024:.0f} KB)")

    try:
        from llama_parse import LlamaParse
        from llama_index.core import SimpleDirectoryReader

        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        parser = LlamaParse(api_key=api_key, result_type="markdown", verbose=False)

        file_extractor = {".pdf": parser}

        # Parse single file
        logger.info("  Parsing PDF (this may take 10-30 seconds)...")
        documents = SimpleDirectoryReader(
            input_files=[str(test_pdf)],
            file_extractor=file_extractor
        ).load_data()

        if documents:
            doc = documents[0]
            logger.info(f"  ✓ Parsed successfully")
            logger.info(f"     - Extracted {len(doc.text)} characters")
            logger.info(f"     - Sample: {doc.text[:150]}...")
            return True
        else:
            logger.error("  ❌ No documents extracted")
            return False

    except Exception as e:
        logger.error(f"  ❌ PDF parsing failed: {e}")
        return False


def test_hierarchical_chunking():
    """Test hierarchical node parser."""
    logger.info("Testing hierarchical chunking...")

    try:
        from llama_index.core import Document
        from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes

        # Create sample document
        sample_text = "This is a test document. " * 100
        doc = Document(text=sample_text)

        # Parse
        node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[512, 128, 64])
        nodes = node_parser.get_nodes_from_documents([doc])
        leaf_nodes = get_leaf_nodes(nodes)

        logger.info(f"  ✓ Created {len(nodes)} total nodes")
        logger.info(f"  ✓ Created {len(leaf_nodes)} leaf nodes")
        logger.info(f"     - Chunk sizes: [512, 128, 64]")

        return True
    except Exception as e:
        logger.error(f"  ❌ Hierarchical chunking failed: {e}")
        return False


def test_pinecone_connection():
    """Test Pinecone connection."""
    logger.info("Testing Pinecone connection...")

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "diabetes-medical-knowledge")

    if not api_key:
        logger.error("  ❌ PINECONE_API_KEY not set")
        return False

    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)

        stats = index.describe_index_stats()
        total_vectors = stats.get('total_vector_count', 0)

        logger.info(f"  ✓ Connected to Pinecone index: {index_name}")
        logger.info(f"     - Total vectors: {total_vectors}")

        namespaces = stats.get('namespaces', {})
        if namespaces:
            logger.info(f"     - Namespaces:")
            for ns, ns_stats in namespaces.items():
                logger.info(f"        - {ns}: {ns_stats.get('vector_count', 0)} vectors")

        return True
    except Exception as e:
        logger.error(f"  ❌ Pinecone connection failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("="*80)
    logger.info("LLAMAPARSE SETUP VALIDATION")
    logger.info("="*80 + "\n")

    tests = [
        ("Imports", test_imports),
        ("Environment", test_environment),
        ("LlamaParse Parser", test_llamaparse_parser),
        ("Hierarchical Chunking", test_hierarchical_chunking),
        ("Pinecone Connection", test_pinecone_connection),
        ("PDF Parsing", test_pdf_parsing),  # Last (slowest)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
        print()  # Blank line between tests

    # Summary
    logger.info("="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        logger.info(f"  {status}: {test_name}")

    logger.info(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n✓ All tests passed! You can run the full ingestion:")
        logger.info("  python scripts/ingest_with_llamaparse.py")
    else:
        logger.error("\n❌ Some tests failed. Fix the issues above before ingestion.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
