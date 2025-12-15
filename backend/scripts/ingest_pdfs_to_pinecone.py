"""Ingest PDF documents from rag_docs directory into Pinecone with namespace-specific strategies."""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.rag_service import (
    get_rag_service,
    NAMESPACE_CLINICAL_SAFETY,
    NAMESPACE_CULTURAL_DIET,
    NAMESPACE_LIFESTYLE_PATTERNS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PDF processing libraries
PDFPLUMBER_AVAILABLE = False
PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pass

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    pass


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text content
    """
    text_content = []
    
    # Try pdfplumber first (better for structured PDFs)
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_content.append(f"Page {page_num}:\n{text}\n")
            logger.info(f"Extracted text from {pdf_path.name} using pdfplumber ({len(pdf.pages)} pages)")
            return "\n".join(text_content)
        except Exception as e:
            logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}, trying PyMuPDF")
    
    # Fallback to PyMuPDF
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text:
                    text_content.append(f"Page {page_num}:\n{text}\n")
            doc.close()
            logger.info(f"Extracted text from {pdf_path.name} using PyMuPDF ({len(doc)} pages)")
            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"PyMuPDF failed for {pdf_path.name}: {e}")
    
    raise RuntimeError(f"Could not extract text from {pdf_path}. Install pdfplumber or pymupdf.")


def chunk_with_headers(text: str, source: str, min_chunk_size: int = 200, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """Chunk text preserving headers (for clinical safety documents).
    
    Args:
        text: Full text content
        source: Source document name
        min_chunk_size: Minimum chunk size in characters
        max_chunk_size: Maximum chunk size in characters
        
    Returns:
        List of chunk dictionaries with header-preserved content
    """
    chunks = []
    
    # Split by common header patterns (lines that are all caps, numbered sections, etc.)
    lines = text.split('\n')
    current_header_stack = []  # Track header hierarchy
    current_chunk = []
    current_chunk_size = 0
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Detect headers (all caps, numbered sections, bold patterns)
        is_header = (
            line_stripped.isupper() and len(line_stripped) > 3 and len(line_stripped) < 100
            or re.match(r'^\d+\.?\s+[A-Z]', line_stripped)  # Numbered sections
            or re.match(r'^[A-Z][A-Z\s]{3,}', line_stripped)  # Title case headers
            or line_stripped.endswith(':') and len(line_stripped) < 80
        )
        
        if is_header:
            # Save current chunk if it has content
            if current_chunk_size >= min_chunk_size:
                header_path = " > ".join(current_header_stack) if current_header_stack else "Introduction"
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "content": f"Header: {header_path}\n{chunk_text}",
                    "metadata": {
                        "source": source,
                        "header_path": header_path,
                        "tags": [h.lower().replace(" ", "_") for h in current_header_stack],
                    }
                })
            
            # Update header stack (simplified: just add to stack, could be smarter)
            if len(current_header_stack) < 3:  # Limit depth
                current_header_stack.append(line_stripped)
            else:
                current_header_stack[-1] = line_stripped
            
            # Start new chunk
            current_chunk = [line_stripped]
            current_chunk_size = len(line_stripped)
        else:
            # Add to current chunk
            current_chunk.append(line_stripped)
            current_chunk_size += len(line_stripped) + 1
            
            # Split if chunk too large
            if current_chunk_size >= max_chunk_size:
                header_path = " > ".join(current_header_stack) if current_header_stack else "Introduction"
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "content": f"Header: {header_path}\n{chunk_text}",
                    "metadata": {
                        "source": source,
                        "header_path": header_path,
                        "tags": [h.lower().replace(" ", "_") for h in current_header_stack],
                    }
                })
                current_chunk = []
                current_chunk_size = 0
    
    # Add final chunk
    if current_chunk_size >= min_chunk_size:
        header_path = " > ".join(current_header_stack) if current_header_stack else "Introduction"
        chunk_text = "\n".join(current_chunk)
        chunks.append({
            "content": f"Header: {header_path}\n{chunk_text}",
            "metadata": {
                "source": source,
                "header_path": header_path,
                "tags": [h.lower().replace(" ", "_") for h in current_header_stack],
            }
        })
    
    return chunks


def chunk_simple(text: str, source: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """Simple chunking with overlap (for lifestyle patterns).
    
    Args:
        text: Full text content
        source: Source document name
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        
    Returns:
        List of chunk dictionaries
    """
    chunks = []
    start = 0
    text_length = len(text)
    prev_start = -1  # Track previous start to detect infinite loops
    
    logger.info(f"Chunking text of length {text_length} characters with chunk_size={chunk_size}, overlap={overlap}")
    
    while start < text_length:
        # Safety check: prevent infinite loop
        if start <= prev_start:
            logger.warning(f"Infinite loop detected at position {start}. Breaking chunk at current position.")
            chunk_text = text[start:start + chunk_size].strip()
            if len(chunk_text) > 100:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "source": source,
                        "tags": ["lifestyle", "guidelines"],
                    }
                })
            break
        
        prev_start = start
        end = min(start + chunk_size, text_length)
        chunk_text = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_length:
            last_period = chunk_text.rfind('.')
            last_newline = chunk_text.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.7:  # Only break if we're at least 70% through
                chunk_text = chunk_text[:break_point + 1]
                end = start + break_point + 1
        
        if len(chunk_text.strip()) > 100:  # Only add substantial chunks
            chunks.append({
                "content": chunk_text.strip(),
                "metadata": {
                    "source": source,
                    "tags": ["lifestyle", "guidelines"],
                }
            })
        
        # Ensure we always advance
        new_start = end - overlap
        if new_start <= start:
            new_start = start + 1  # Force advancement by at least 1 character
        start = new_start
        
        # Log progress for large documents
        if len(chunks) % 100 == 0:
            logger.info(f"Created {len(chunks)} chunks so far (at position {start}/{text_length})")
    
    logger.info(f"Finished chunking: created {len(chunks)} chunks from {text_length} characters")
    return chunks


def convert_food_data_to_narratives(text: str, source: str) -> List[Dict[str, Any]]:
    """Convert food data tables to narrative format (for cultural diet).
    
    Args:
        text: Extracted text (may contain tables)
        source: Source document name
        
    Returns:
        List of narrative-formatted food documents
    """
    narratives = []
    
    # Try to extract table-like data (rows with numbers)
    lines = text.split('\n')
    current_food = None
    food_data = {}
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Look for food names (usually at start of line, may have numbers after)
        # Pattern: Food name followed by numbers (calories, carbs, etc.)
        food_match = re.match(r'^([A-Za-z\s]+?)(?:\s+(\d+(?:\.\d+)?))', line_stripped)
        
        if food_match:
            # Save previous food if exists
            if current_food and food_data:
                narrative = create_food_narrative(current_food, food_data)
                if narrative:
                    narratives.append({
                        "content": narrative,
                        "metadata": {
                            "source": source,
                            "tags": ["food", "nutrition", "singapore"],
                            "dish_name": current_food,
                        }
                    })
            
            # Start new food
            current_food = food_match.group(1).strip()
            food_data = {}
            if food_match.group(2):
                food_data['value1'] = float(food_match.group(2))
        else:
            # Try to extract numeric data (calories, carbs, etc.)
            numbers = re.findall(r'(\d+(?:\.\d+)?)', line_stripped)
            if numbers and current_food:
                if 'calories' in line_stripped.lower() or 'kcal' in line_stripped.lower():
                    food_data['calories'] = float(numbers[0])
                elif 'carb' in line_stripped.lower():
                    food_data['carbs'] = float(numbers[0])
                elif 'sodium' in line_stripped.lower() or 'na' in line_stripped.lower():
                    food_data['sodium'] = float(numbers[0])
                elif 'gi' in line_stripped.lower() or 'glycemic' in line_stripped.lower():
                    food_data['gi'] = float(numbers[0])
    
    # Save last food
    if current_food and food_data:
        narrative = create_food_narrative(current_food, food_data)
        if narrative:
            narratives.append({
                "content": narrative,
                "metadata": {
                    "source": source,
                    "tags": ["food", "nutrition", "singapore"],
                    "dish_name": current_food,
                }
            })
    
    # If no structured data found, chunk as regular text
    if not narratives:
        chunks = chunk_simple(text, source, chunk_size=800)
        for chunk in chunks:
            chunk['metadata']['tags'] = ["food", "nutrition", "singapore"]
        narratives = chunks
    
    return narratives


def create_food_narrative(food_name: str, data: Dict[str, Any]) -> Optional[str]:
    """Create narrative description from food data.
    
    Args:
        food_name: Name of the food
        data: Dictionary with nutritional data
        
    Returns:
        Narrative string or None
    """
    parts = [f"{food_name} is a Singaporean dish"]
    
    if 'calories' in data:
        parts.append(f"containing approximately {data['calories']:.0f} kcal")
    if 'carbs' in data:
        parts.append(f"with {data['carbs']:.0f}g of carbohydrates")
    if 'gi' in data:
        gi_level = "high" if data['gi'] > 70 else "medium" if data['gi'] > 55 else "low"
        parts.append(f"Glycemic Index: {data['gi']:.0f} ({gi_level} GI)")
    if 'sodium' in data:
        parts.append(f"Sodium content: {data['sodium']:.0f}mg")
    
    if len(parts) > 1:
        return ". ".join(parts) + "."
    return None


def ingest_pdf_to_namespace(pdf_path: Path, namespace: str) -> int:
    """Ingest a single PDF into specified namespace with appropriate chunking strategy.
    
    Args:
        pdf_path: Path to PDF file
        namespace: Target namespace (clinical-safety, cultural-diet, lifestyle-patterns)
        
    Returns:
        Number of chunks ingested
    """
    rag = get_rag_service()
    if not rag.is_available():
        logger.warning("Pinecone not configured. Skipping PDF ingestion.")
        return 0
    
    logger.info(f"Processing PDF: {pdf_path.name} for namespace: {namespace}")
    
    try:
        # Extract text
        logger.info(f"Extracting text from {pdf_path.name}...")
        text = extract_text_from_pdf(pdf_path)
        source = pdf_path.stem  # Filename without extension
        logger.info(f"Extracted {len(text)} characters from {pdf_path.name}")
        
        # Chunk based on namespace strategy
        logger.info(f"Chunking text using strategy for namespace: {namespace}")
        if namespace == NAMESPACE_CLINICAL_SAFETY:
            chunks = chunk_with_headers(text, source)
        elif namespace == NAMESPACE_CULTURAL_DIET:
            chunks = convert_food_data_to_narratives(text, source)
        else:  # NAMESPACE_LIFESTYLE_PATTERNS
            chunks = chunk_simple(text, source)
        
        logger.info(f"Created {len(chunks)} chunks from {pdf_path.name}")
        
        if not chunks:
            logger.warning(f"No chunks extracted from {pdf_path.name}")
            return 0
        
        # Add IDs to chunks
        for idx, chunk in enumerate(chunks):
            chunk["id"] = f"{namespace}_{source}_{idx}"
        
        # Ingest to Pinecone
        rag.ingest_with_metadata(chunks, namespace)
        logger.info(f"Successfully ingested {len(chunks)} chunks from {pdf_path.name} into {namespace}")
        return len(chunks)
        
    except Exception as e:
        logger.error(f"Error ingesting {pdf_path.name}: {e}", exc_info=True)
        return 0


def ingest_all_pdfs():
    """Ingest all PDFs from rag_docs directory into appropriate namespaces."""
    rag_docs_dir = backend_dir / "rag_docs"
    
    if not rag_docs_dir.exists():
        logger.error(f"rag_docs directory not found: {rag_docs_dir}")
        return
    
    # Clinical Safety PDFs
    clinical_safety_dir = rag_docs_dir / "clinical_safety_docs"
    if clinical_safety_dir.exists():
        logger.info("Ingesting Clinical Safety PDFs...")
        pdf_files = list(clinical_safety_dir.glob("*.pdf"))
        total_chunks = 0
        for pdf_file in pdf_files:
            chunks = ingest_pdf_to_namespace(pdf_file, NAMESPACE_CLINICAL_SAFETY)
            total_chunks += chunks
        logger.info(f"Clinical Safety: Ingested {total_chunks} total chunks from {len(pdf_files)} PDFs")
    
    # Cultural Diet PDFs
    cultural_diet_dir = rag_docs_dir / "cultural_diet_docs"
    if cultural_diet_dir.exists():
        logger.info("Ingesting Cultural Diet PDFs...")
        pdf_files = list(cultural_diet_dir.glob("*.pdf"))
        total_chunks = 0
        for pdf_file in pdf_files:
            chunks = ingest_pdf_to_namespace(pdf_file, NAMESPACE_CULTURAL_DIET)
            total_chunks += chunks
        logger.info(f"Cultural Diet: Ingested {total_chunks} total chunks from {len(pdf_files)} PDFs")
    
    # Lifestyle Patterns PDFs
    lifestyle_patterns_dir = rag_docs_dir / "lifestyle_patterns_docs"
    if lifestyle_patterns_dir.exists():
        logger.info("Ingesting Lifestyle Patterns PDFs...")
        pdf_files = list(lifestyle_patterns_dir.glob("*.pdf"))
        total_chunks = 0
        for pdf_file in pdf_files:
            chunks = ingest_pdf_to_namespace(pdf_file, NAMESPACE_LIFESTYLE_PATTERNS)
            total_chunks += chunks
        logger.info(f"Lifestyle Patterns: Ingested {total_chunks} total chunks from {len(pdf_files)} PDFs")


if __name__ == "__main__":
    logger.info("Starting PDF ingestion to Pinecone...")
    
    # Check for Pinecone API key
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not found. RAG service will use fallback responses.")
        logger.info("To enable RAG, set PINECONE_API_KEY environment variable.")
    
    # Check for PDF libraries
    if not PDFPLUMBER_AVAILABLE and not PYMUPDF_AVAILABLE:
        logger.error("No PDF parsing library available. Install pdfplumber or pymupdf.")
        sys.exit(1)
    
    # Ingest all PDFs
    ingest_all_pdfs()
    
    logger.info("PDF ingestion complete!")

