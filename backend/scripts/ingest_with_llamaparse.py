"""Enhanced PDF ingestion using LlamaParse + LlamaIndex with hierarchical chunking and metadata extraction.

This script provides superior PDF parsing compared to pdfplumber/PyMuPDF:
- Preserves table structures as Markdown
- Hierarchical chunking with parent-child relationships
- Automatic metadata extraction (titles, questions answered)
- Better semantic search through rich metadata

Requirements:
    pip install llama-parse llama-index-core llama-index-vector-stores-pinecone
    pip install llama-index-embeddings-openai
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(backend_dir / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LlamaParse components
try:
    from llama_parse import LlamaParse
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
    from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
    from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
    from llama_index.vector_stores.pinecone import PineconeVectorStore
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core import Settings
    from pinecone import Pinecone

    LLAMAPARSE_AVAILABLE = True
    logger.info("✓ LlamaParse and LlamaIndex components loaded successfully")
except ImportError as e:
    LLAMAPARSE_AVAILABLE = False
    logger.error(f"❌ LlamaParse dependencies not available: {e}")
    logger.error("Install with: pip install llama-parse llama-index llama-index-vector-stores-pinecone llama-index-embeddings-openai")
    sys.exit(1)

# Import RAG service constants
from app.services.rag_service import (
    NAMESPACE_CLINICAL_SAFETY,
    NAMESPACE_CULTURAL_DIET,
    NAMESPACE_LIFESTYLE_PATTERNS,
)


def validate_environment() -> tuple[str, str, str]:
    """Validate required environment variables.

    Returns:
        Tuple of (llama_cloud_key, pinecone_key, openai_key)

    Raises:
        ValueError if required keys are missing
    """
    llama_key = os.getenv("LLAMA_CLOUD_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    pinecone_index = os.getenv("PINECONE_INDEX", "diabetes-medical-knowledge")

    missing = []
    if not llama_key:
        missing.append("LLAMA_CLOUD_API_KEY (get free key from cloud.llamaindex.ai)")
    if not pinecone_key:
        missing.append("PINECONE_API_KEY")
    if not openai_key:
        missing.append("OPENAI_API_KEY")

    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    logger.info("✓ Environment variables validated")
    logger.info(f"  Pinecone Index: {pinecone_index}")

    return llama_key, pinecone_key, openai_key


def setup_llamaparse_parser(api_key: str) -> LlamaParse:
    """Setup LlamaParse parser with optimal settings.

    Args:
        api_key: LlamaCloud API key

    Returns:
        Configured LlamaParse instance
    """
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",  # CRITICAL: Preserves tables as Markdown
        verbose=True,
        language="en",
        num_workers=4,  # Parallel processing
        invalidate_cache=False,  # Use cache for repeated runs
    )

    logger.info("✓ LlamaParse parser configured")
    logger.info("  - Result type: markdown (preserves table structure)")
    logger.info("  - Parallel workers: 4")

    return parser


def parse_documents(directory: Path, parser: LlamaParse) -> List:
    """Parse PDF documents using LlamaParse.

    Args:
        directory: Directory containing PDF files
        parser: LlamaParse instance

    Returns:
        List of parsed documents
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    pdf_files = list(directory.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return []

    logger.info(f"Parsing {len(pdf_files)} PDFs from {directory.name}...")
    for pdf in pdf_files:
        logger.info(f"  - {pdf.name} ({pdf.stat().st_size / 1024:.0f} KB)")

    # Setup file extractor
    file_extractor = {".pdf": parser}

    # Load documents
    try:
        documents = SimpleDirectoryReader(
            input_dir=str(directory),
            file_extractor=file_extractor
        ).load_data()

        logger.info(f"✓ Parsed {len(documents)} documents")

        # Show sample
        if documents:
            sample = documents[0].text[:500]
            logger.info(f"  Sample content: {sample}...")

        return documents
    except Exception as e:
        logger.error(f"Failed to parse documents: {e}", exc_info=True)
        raise


def create_hierarchical_nodes(documents: List, chunk_sizes: Optional[List[int]] = None):
    """Create hierarchical nodes with parent-child relationships.

    Args:
        documents: List of parsed documents
        chunk_sizes: List of chunk sizes [parent, middle, leaf]. Default: [2048, 512, 128]

    Returns:
        Tuple of (all_nodes, leaf_nodes)
    """
    if chunk_sizes is None:
        chunk_sizes = [2048, 512, 128]  # Top, middle, leaf

    logger.info(f"Creating hierarchical nodes with chunk sizes: {chunk_sizes}")

    # Create parser
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)

    # Parse nodes
    all_nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(all_nodes)

    logger.info(f"✓ Created {len(all_nodes)} total nodes, {len(leaf_nodes)} leaf nodes")
    logger.info(f"  - Leaf nodes are indexed, but link to parent context")

    return all_nodes, leaf_nodes


def extract_metadata(leaf_nodes: List, openai_key: str):
    """Extract metadata from nodes using LLM.

    Adds:
    - Document title
    - Questions this excerpt answers (improves semantic search)

    Args:
        leaf_nodes: List of leaf nodes
        openai_key: OpenAI API key

    Returns:
        Nodes with enhanced metadata
    """
    logger.info("Extracting metadata from nodes (uses LLM calls)...")
    logger.warning("⚠️  This will incur OpenAI API costs (~$0.001 per node)")

    # Setup extractors
    extractors = [
        TitleExtractor(nodes=5, llm=None),  # Extract title from first 5 nodes
        QuestionsAnsweredExtractor(questions=3, llm=None),  # Generate 3 questions per node
    ]

    # Configure OpenAI settings
    Settings.embed_model = OpenAIEmbedding(api_key=openai_key)

    logger.info(f"  - TitleExtractor: Extracting document titles")
    logger.info(f"  - QuestionsAnsweredExtractor: Generating 3 questions per node")

    # Run extractors
    # Note: LlamaIndex will automatically run extractors during indexing
    # We just log the setup here

    logger.info(f"✓ Metadata extractors configured for {len(leaf_nodes)} nodes")

    return leaf_nodes, extractors


def ingest_to_pinecone(
    leaf_nodes: List,
    namespace: str,
    pinecone_key: str,
    openai_key: str,
    index_name: str = "diabetes-medical-knowledge",
    extractors: Optional[List] = None,
):
    """Ingest nodes to Pinecone vector store.

    Args:
        leaf_nodes: List of leaf nodes to index
        namespace: Pinecone namespace (clinical-safety, cultural-diet, lifestyle-patterns)
        pinecone_key: Pinecone API key
        openai_key: OpenAI API key
        index_name: Pinecone index name
        extractors: List of metadata extractors
    """
    logger.info(f"Ingesting {len(leaf_nodes)} nodes to Pinecone namespace '{namespace}'...")

    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_key)
    pinecone_index = pc.Index(index_name)

    # Get index stats before
    stats_before = pinecone_index.describe_index_stats()
    before_count = stats_before.get('namespaces', {}).get(namespace, {}).get('vector_count', 0)
    logger.info(f"  Current vectors in namespace '{namespace}': {before_count}")

    # Setup vector store
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace=namespace,
    )

    # Setup storage context
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Configure OpenAI embeddings
    Settings.embed_model = OpenAIEmbedding(
        api_key=openai_key,
        model="text-embedding-3-small",  # Latest embedding model
    )

    logger.info("  Using text-embedding-3-small (1536 dimensions)")

    # Create index (this ingests to Pinecone)
    try:
        index = VectorStoreIndex(
            leaf_nodes,
            storage_context=storage_context,
            transformations=extractors if extractors else [],  # Apply metadata extractors
            show_progress=True,
        )

        logger.info("✓ Ingestion complete")

        # Get index stats after
        import time
        time.sleep(2)  # Wait for indexing
        stats_after = pinecone_index.describe_index_stats()
        after_count = stats_after.get('namespaces', {}).get(namespace, {}).get('vector_count', 0)

        new_vectors = after_count - before_count
        logger.info(f"  Vectors in namespace '{namespace}': {after_count} (+{new_vectors})")

        return index

    except Exception as e:
        logger.error(f"Failed to ingest to Pinecone: {e}", exc_info=True)
        raise


def ingest_namespace(
    directory: Path,
    namespace: str,
    parser: LlamaParse,
    pinecone_key: str,
    openai_key: str,
    chunk_sizes: Optional[List[int]] = None,
    use_metadata_extraction: bool = True,
):
    """Complete ingestion pipeline for a namespace.

    Args:
        directory: Directory containing PDFs
        namespace: Pinecone namespace
        parser: LlamaParse instance
        pinecone_key: Pinecone API key
        openai_key: OpenAI API key
        chunk_sizes: Hierarchical chunk sizes
        use_metadata_extraction: Whether to extract metadata (costs API calls)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"INGESTING NAMESPACE: {namespace}")
    logger.info(f"{'='*80}")

    # Step 1: Parse documents
    documents = parse_documents(directory, parser)
    if not documents:
        logger.warning(f"Skipping {namespace} - no documents found")
        return

    # Step 2: Create hierarchical nodes
    all_nodes, leaf_nodes = create_hierarchical_nodes(documents, chunk_sizes)

    # Step 3: Extract metadata (optional, costs API calls)
    extractors = None
    if use_metadata_extraction:
        leaf_nodes, extractors = extract_metadata(leaf_nodes, openai_key)
    else:
        logger.info("Skipping metadata extraction (set use_metadata_extraction=True to enable)")

    # Step 4: Ingest to Pinecone
    ingest_to_pinecone(
        leaf_nodes=leaf_nodes,
        namespace=namespace,
        pinecone_key=pinecone_key,
        openai_key=openai_key,
        extractors=extractors,
    )

    logger.info(f"✓ Completed ingestion for namespace '{namespace}'")


def main():
    """Main ingestion pipeline."""
    logger.info("="*80)
    logger.info("LLAMAPARSE-BASED PDF INGESTION TO PINECONE")
    logger.info("="*80)

    # Validate environment
    try:
        llama_key, pinecone_key, openai_key = validate_environment()
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        return

    # Setup parser
    parser = setup_llamaparse_parser(llama_key)

    # Define directories
    rag_docs_dir = backend_dir / "rag_docs"

    namespaces_to_ingest = [
        {
            "directory": rag_docs_dir / "clinical_safety_docs",
            "namespace": NAMESPACE_CLINICAL_SAFETY,
            "chunk_sizes": [2048, 512, 128],  # Larger chunks for clinical guidelines
            "use_metadata": True,  # Extract metadata for better search
        },
        {
            "directory": rag_docs_dir / "cultural_diet_docs",
            "namespace": NAMESPACE_CULTURAL_DIET,
            "chunk_sizes": [1536, 384, 128],  # Medium chunks for food tables
            "use_metadata": True,
        },
        {
            "directory": rag_docs_dir / "lifestyle_patterns_docs",
            "namespace": NAMESPACE_LIFESTYLE_PATTERNS,
            "chunk_sizes": [2048, 512, 128],  # Larger chunks for lifestyle guidance
            "use_metadata": True,
        },
    ]

    # Track success/failure
    results = {"success": [], "failed": []}

    # Ingest each namespace
    for config in namespaces_to_ingest:
        try:
            logger.info(f"\nProcessing namespace: {config['namespace']}")
            ingest_namespace(
                directory=config["directory"],
                namespace=config["namespace"],
                parser=parser,
                pinecone_key=pinecone_key,
                openai_key=openai_key,
                chunk_sizes=config["chunk_sizes"],
                use_metadata_extraction=config["use_metadata"],
            )
            results["success"].append(config["namespace"])
        except Exception as e:
            logger.error(f"Failed to ingest {config['namespace']}: {e}")
            results["failed"].append((config["namespace"], str(e)))

            # Check for numpy compatibility error
            if "numpy.dtype size changed" in str(e):
                logger.error("\n" + "="*80)
                logger.error("NUMPY BINARY INCOMPATIBILITY DETECTED")
                logger.error("="*80)
                logger.error("This error occurs when packages are compiled against different numpy versions.")
                logger.error("\nQuick Fix:")
                logger.error("  1. Run: bash scripts/fix_numpy_compatibility.sh")
                logger.error("  2. Or manually: pip uninstall -y numpy scipy pandas llama-index-core")
                logger.error("                  pip install numpy scipy pandas llama-index-core")
                logger.error("\nThen retry ingestion.")
                logger.error("="*80 + "\n")

            continue

    logger.info("\n" + "="*80)
    logger.info("INGESTION SUMMARY")
    logger.info("="*80)

    if results["success"]:
        logger.info(f"✓ Successfully ingested {len(results['success'])} namespaces:")
        for ns in results["success"]:
            logger.info(f"  - {ns}")

    if results["failed"]:
        logger.error(f"\n❌ Failed to ingest {len(results['failed'])} namespaces:")
        for ns, error in results["failed"]:
            logger.error(f"  - {ns}: {error[:100]}...")

    logger.info("\n" + "="*80)

    if not results["failed"]:
        logger.info("✓ ALL INGESTION COMPLETE")
        logger.info("\nNext steps:")
        logger.info("1. Verify vectors in Pinecone dashboard")
        logger.info("2. Test RAG search: python -m app.services.rag_service")
        logger.info("3. Run notebook: jupyter notebook notebooks/test_rag_pipeline.ipynb")
    else:
        logger.warning("⚠️  PARTIAL INGESTION COMPLETE")
        logger.warning(f"  {len(results['success'])} succeeded, {len(results['failed'])} failed")
        logger.warning("\nFix errors above and re-run ingestion.")

    logger.info("="*80)


if __name__ == "__main__":
    if not LLAMAPARSE_AVAILABLE:
        logger.error("LlamaParse dependencies not available. Exiting.")
        sys.exit(1)

    main()
