"""RAG service for medical knowledge retrieval using Pinecone with namespace isolation."""
from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Any, Optional, Dict, List

from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone.exceptions import PineconeException

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Namespace constants for agent isolation
# IMPORTANT: Each agent MUST use ONLY their assigned namespace:
# - Clinical Safety Agent → NAMESPACE_CLINICAL_SAFETY (via query_clinical_safety())
# - Cultural Dietitian Agent → NAMESPACE_CULTURAL_DIET (via query_cultural_diet())
# - Lifestyle Analyst Agent → NAMESPACE_LIFESTYLE_PATTERNS (via query_lifestyle_patterns())
# Cross-namespace queries are NOT allowed for strict isolation.
NAMESPACE_CLINICAL_SAFETY = "clinical_safety"
NAMESPACE_CULTURAL_DIET = "dietician_docs"
NAMESPACE_LIFESTYLE_PATTERNS = "lifestyle-patterns"


class RAGService:
    """Service for RAG operations using Pinecone vector database.
    
    This service handles:
    - Ingesting medical knowledge (drugs, foods, clinical guidelines)
    - Semantic search for retrieving relevant context
    - Multi-tenant support using namespaces
    """
    
    def __init__(self, index_name: Optional[str] = None):
        """Initialize RAG service with Pinecone client.
        
        Args:
            index_name: Name of the Pinecone index. Defaults to environment variable
                       or 'diabetes-medical-knowledge'
        """
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            logger.warning("PINECONE_API_KEY not found. RAG operations will be disabled.")
            self.pc = None
            self.index = None
            return
        
        try:
            self.pc = Pinecone(api_key=self.api_key)
            self.index_name = index_name or os.getenv("PINECONE_INDEX", "diabetes-medical-knowledge")
            self.index = self.pc.Index(self.index_name)
            logger.info(f"RAG service initialized with index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self.pc = None
            self.index = None
    
    def is_available(self) -> bool:
        """Check if RAG service is available (API key configured)."""
        available = self.index is not None
        if not available:
            logger.debug("[RAG] Service not available - PINECONE_API_KEY not configured or index not initialized")
        return available
    
    def ingest_documents(
        self,
        documents: list[str],
        index_type: str = "general",
        namespace: Optional[str] = None,
    ) -> None:
        """Ingest documents into Pinecone index.
        
        Args:
            documents: List of document strings to ingest
            index_type: Type of knowledge (e.g., 'drug', 'food', 'clinical')
            namespace: Optional namespace for data isolation. Defaults to index_type
        """
        if not self.is_available():
            logger.warning("Pinecone not configured. Skipping document ingestion.")
            return
        
        namespace = namespace or index_type
        
        # Prepare records for upsert
        records = []
        for idx, doc in enumerate(documents):
            record = {
                "_id": f"{index_type}_{idx}",
                "text": doc.strip(),
                "index_type": index_type,
            }
            records.append(record)
        
        try:
            # Upsert in batches (max 96 records per batch for text)
            batch_size = 96
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                self.index.upsert_records(namespace, batch)
                logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} records) to namespace '{namespace}'")
                time.sleep(0.1)  # Rate limiting
            
            # Wait for indexing to complete
            logger.info(f"Waiting 10 seconds for vectors to be indexed...")
            time.sleep(10)
            logger.info(f"Successfully ingested {len(records)} documents into namespace '{namespace}'")
            
        except PineconeException as e:
            logger.error(f"Pinecone error during ingestion: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during ingestion: {e}", exc_info=True)
            raise
    
    def search(
        self,
        query: str,
        index_type: Optional[str] = None,
        top_k: int = 5,
        namespace: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search for relevant documents using semantic search.
        
        WARNING: This is an internal method. Agents should use namespace-specific methods:
        - query_clinical_safety() for Clinical Safety Agent
        - query_cultural_diet() for Cultural Dietitian Agent
        
        Args:
            query: Search query text
            index_type: Filter by knowledge type (e.g., 'drug', 'food', 'clinical')
            top_k: Number of results to return
            namespace: REQUIRED - Specific namespace to search (clinical_safety, dietician_docs, lifestyle-patterns)
            
        Returns:
            List of search results with content, score, and metadata
        """
        if not self.is_available():
            logger.warning("[RAG] Search skipped - Pinecone not configured")
            return []
        
        # Validate namespace is one of the allowed namespaces
        allowed_namespaces = [NAMESPACE_CLINICAL_SAFETY, NAMESPACE_CULTURAL_DIET, NAMESPACE_LIFESTYLE_PATTERNS]
        if namespace and namespace not in allowed_namespaces:
            logger.error(f"[RAG] Invalid namespace '{namespace}' - must be one of {allowed_namespaces}")
            return []
        
        # Require namespace parameter for strict isolation
        if not namespace:
            logger.error("[RAG] search() called without namespace - NAMESPACE ISOLATION VIOLATION!")
            logger.error("[RAG] Use namespace-specific query methods: query_clinical_safety(), query_cultural_diet(), query_lifestyle_patterns()")
            return []
        
        logger.info(f"[RAG] Search called: namespace='{namespace}' (ISOLATED), query='{query[:80]}...', top_k={top_k}")
        
        try:
            # Build query with optional metadata filter
            query_dict = {
                "top_k": top_k * 2,  # Get more candidates for reranking
                "inputs": {
                    "text": query
                }
            }
            
            # Add metadata filter if index_type specified
            if index_type:
                query_dict["filter"] = {"index_type": {"$eq": index_type}}
                logger.debug(f"[RAG] Added metadata filter: index_type={index_type}")
            
            # Perform search with reranking for better results
            logger.debug(f"[RAG] Executing Pinecone search in namespace '{namespace}'...")
            results = self.index.search(
                namespace=namespace,
                query=query_dict,
                rerank={
                    "model": "bge-reranker-v2-m3",
                    "top_n": top_k,
                    "rank_fields": ["text"]  # Index uses "text" field
                }
            )
            
            # Format results
            formatted_results = []
            for hit in results.result.hits:
                # Index uses "text" field, but we return as "content" for consistency
                content = hit.fields.get("text") or hit.fields.get("content", "")
                formatted_results.append({
                    "id": hit["_id"],
                    "content": content,
                    "score": hit["_score"],
                    "metadata": {
                        "index_type": hit.fields.get("index_type", "unknown"),
                        "source": hit.fields.get("source", "unknown"),
                        "tags": hit.fields.get("tags", "").split(", ") if isinstance(hit.fields.get("tags"), str) else hit.fields.get("tags", []),
                    }
                })
            
            logger.info(f"[RAG] Search completed: {len(formatted_results)} results from namespace '{namespace}' for query: '{query[:50]}...'")
            if formatted_results:
                top_score = formatted_results[0].get("score", 0)
                top_source = formatted_results[0].get("metadata", {}).get("source", "Unknown")
                logger.debug(f"[RAG] Top result - Score: {top_score:.4f}, Source: {top_source}")
            
            return formatted_results
            
        except PineconeException as e:
            logger.error(f"Pinecone error during search: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            return []
    
    def get_context_for_llm(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 3,
        include_citations: bool = True,  # Always True - citations are mandatory
    ) -> str:
        """Get formatted context string for LLM prompt with STRICT namespace isolation.
        
        IMPORTANT: This method requires a namespace parameter. It will NOT search all namespaces.
        Each agent must specify their namespace to maintain isolation.
        
        Args:
            query: Search query
            namespace: REQUIRED - Specific namespace to search (clinical_safety, dietician_docs, lifestyle-patterns)
                      MUST be provided - no default to prevent cross-namespace queries
            top_k: Number of results to return
            include_citations: Whether to include source citations (defaults to True - citations are mandatory)
            
        Returns:
            Formatted context string with citations from the specified namespace only.
            Citations are ALWAYS included when RAG is used - they are mandatory.
        """
        if not self.is_available():
            logger.debug("[RAG] get_context_for_llm skipped - RAG service not available")
            return ""
        
        # STRICT NAMESPACE ISOLATION: Require namespace parameter
        if not namespace:
            logger.error("[RAG] get_context_for_llm called without namespace - NAMESPACE ISOLATION VIOLATION!")
            logger.error("[RAG] Each agent must specify their namespace. No cross-namespace queries allowed.")
            return ""
        
        # Validate namespace is one of the allowed namespaces
        allowed_namespaces = [NAMESPACE_CLINICAL_SAFETY, NAMESPACE_CULTURAL_DIET, NAMESPACE_LIFESTYLE_PATTERNS]
        if namespace not in allowed_namespaces:
            logger.error(f"[RAG] Invalid namespace '{namespace}' - must be one of {allowed_namespaces}")
            return ""
        
        logger.info(f"[RAG] get_context_for_llm called: query='{query[:80]}...', namespace='{namespace}' (ISOLATED), top_k={top_k}")
        logger.info(f"[RAG] NAMESPACE ISOLATION: Querying ONLY '{namespace}' namespace")
        
        # Search ONLY the specified namespace
        results = self.search(query, namespace=namespace, top_k=top_k)
        logger.info(f"[RAG] Searched namespace '{namespace}' ONLY, found {len(results)} results")
        
        # Format as context string
        if not results:
            logger.warning(f"[RAG] No results found in namespace '{namespace}' for query: '{query[:80]}...'")
            return ""
        
        # Citations are MANDATORY when RAG is used - always include them (ignore include_citations parameter)
        context_parts = ["Relevant Medical Knowledge (with mandatory citations):"]
        source_names = []  # Collect all source names for citation examples
        for idx, result in enumerate(results, 1):
            content = result['content']
            # Extract source information - citations are ALWAYS included
            source = result.get('metadata', {}).get('source', 'Unknown')
            tags = result.get('metadata', {}).get('tags', [])
            
            # Format citation prominently at the START for better visibility
            if source != 'Unknown':
                # Clean source name for better readability (remove file extensions, underscores)
                clean_source = source.replace('_', ' ').replace('.pdf', '').replace('.txt', '')
                citation_header = f"Source: {clean_source}"
                source_names.append(clean_source)  # Track for examples
            else:
                citation_header = "Source: Unknown"
            
            if tags:
                citation_header += f" | Tags: {', '.join(tags[:3])}"
            
            # Format: Citation FIRST, then content - makes citations more prominent
            # Include explicit citation template in the content itself
            context_parts.append(
                f"[{idx}] 📖 {citation_header}\n"
                f"Content: {content}\n"
                f"When using this information, you MUST cite it as: 'According to {clean_source if source != 'Unknown' else 'the source'}, ...'"
            )
        
        # Add explicit instruction about citations with actual source names from results
        citation_examples = ""
        if source_names:
            unique_sources = list(set(source_names))[:3]  # Get unique sources, max 3
            citation_examples = "\n\nACTUAL Source Names from above (use these EXACT names):\n"
            for src in unique_sources:
                citation_examples += f"- {src}\n"
            citation_examples += "\nExample citations using ACTUAL sources:\n"
            for src in unique_sources[:2]:  # Show 2 examples
                citation_examples += f"- 'According to {src}, ...'\n"
        
        context_parts.append(
            "\n⚠️⚠️⚠️ MANDATORY CITATION REQUIREMENT ⚠️⚠️⚠️"
            "\nYou MUST cite the source for EVERY piece of information you use from above."
            f"{citation_examples}"
            "\n\nREQUIRED Citation Format (use the EXACT source names shown above):"
            "\n- 'According to [EXACT Source Name], ...'"
            "\n- 'Based on [EXACT Source Name], ...'"
            "\n- 'Per [EXACT Source Name], ...'"
            "\n- 'The [EXACT Source Name] states that...'"
            "\n\n❌ FORBIDDEN: Never mention information from RAG without citing the EXACT source name"
            "\n✅ REQUIRED: Every sentence using RAG information must include the source name"
            "\n✅ REQUIRED: Copy the source name EXACTLY as shown above (do not modify it)"
        )
        
        context_str = "\n".join(context_parts)
        logger.info(f"[RAG] Formatted context string with MANDATORY citations: {len(context_str)} characters from {len(results)} results")
        logger.info(f"[RAG] Citations included for all {len(results)} results - citations are mandatory when RAG is used")
        return context_str
    
    # Namespace-specific query methods for agent isolation
    
    def query_clinical_safety(
        self,
        query: str,
        patient_context: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Query clinical safety namespace for drug interactions, contraindications, etc.
        
        IMPORTANT: This method ONLY queries the 'clinical_safety' namespace.
        Use this method for Clinical Safety Agent queries.
        
        Args:
            query: Search query (e.g., "metformin kidney disease contraindication")
            patient_context: Optional patient context to enhance query (age, conditions, medications)
            top_k: Number of results
            
        Returns:
            List of relevant clinical safety documents from clinical_safety namespace only
        """
        if not self.is_available():
            logger.warning("[RAG] Clinical Safety query skipped - RAG service not available")
            return []
        
        logger.info(f"[RAG] Clinical Safety query initiated: '{query[:100]}...' (top_k={top_k})")
        logger.info(f"[RAG] NAMESPACE ISOLATION: Querying ONLY '{NAMESPACE_CLINICAL_SAFETY}' namespace")
        
        # Enhance query with patient context if provided
        enhanced_query = query
        if patient_context:
            context_parts = [query]
            if patient_context.get('age'):
                context_parts.append(f"age {patient_context['age']}")
            if patient_context.get('conditions'):
                context_parts.append(f"conditions {', '.join(patient_context['conditions'])}")
            if patient_context.get('medications'):
                context_parts.append(f"medications {', '.join(patient_context['medications'])}")
            enhanced_query = " ".join(context_parts)
            logger.debug(f"[RAG] Enhanced query with patient context: '{enhanced_query[:150]}...'")
        
        # STRICT NAMESPACE ISOLATION: Only query clinical_safety namespace
        results = self.search(enhanced_query, namespace=NAMESPACE_CLINICAL_SAFETY, top_k=top_k)
        logger.info(f"[RAG] Clinical Safety query returned {len(results)} results from namespace '{NAMESPACE_CLINICAL_SAFETY}' ONLY")
        if results:
            logger.debug(f"[RAG] Top result source: {results[0].get('metadata', {}).get('source', 'Unknown')}")
        
        return results
    
    def query_cultural_diet(
        self,
        dish_name: str,
        top_k: int = 1,
    ) -> List[Dict[str, Any]]:
        """Query cultural diet namespace for Singaporean food nutritional data.
        
        IMPORTANT: This method ONLY queries the 'dietician_docs' namespace.
        Use this method for Cultural Dietitian Agent queries.
        
        Args:
            dish_name: Name of the dish (e.g., "Chicken Rice", "Char Kway Teow")
            top_k: Number of results (usually 1 for exact match)
            
        Returns:
            List of nutritional information for the dish from dietician_docs namespace only
        """
        if not self.is_available():
            logger.warning(f"[RAG] Cultural Diet query skipped for '{dish_name}' - RAG service not available")
            return []
        
        logger.info(f"[RAG] Cultural Diet query initiated for dish: '{dish_name}' (top_k={top_k})")
        logger.info(f"[RAG] NAMESPACE ISOLATION: Querying ONLY '{NAMESPACE_CULTURAL_DIET}' namespace")
        
        # Try exact match first, then semantic search
        query = f"{dish_name} nutritional profile calories carbohydrates Singapore"
        
        # STRICT NAMESPACE ISOLATION: Only query dietician_docs namespace
        results = self.search(query, namespace=NAMESPACE_CULTURAL_DIET, top_k=top_k)
        logger.info(f"[RAG] Cultural Diet query returned {len(results)} results from namespace '{NAMESPACE_CULTURAL_DIET}' ONLY")
        if results:
            metadata = results[0].get('metadata', {})
            logger.debug(f"[RAG] Top result - Dish: {metadata.get('dish_name', 'N/A')}, Source: {metadata.get('source', 'Unknown')}, Carbs: {metadata.get('carbs_g', 'N/A')}g")
        else:
            logger.warning(f"[RAG] No nutritional data found in RAG for dish: '{dish_name}'")
        
        return results
    
    def query_lifestyle_patterns(
        self,
        query: str,
        patient_context: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Query lifestyle patterns namespace for exercise, glucose targets, etc.
        
        IMPORTANT: This method ONLY queries the 'lifestyle-patterns' namespace.
        Use this method for Lifestyle Analyst Agent queries.
        
        Args:
            query: Search query (e.g., "glucose target Type 2 Diabetes age 45")
            patient_context: Optional patient context to enhance query
            top_k: Number of results
            
        Returns:
            List of relevant lifestyle guidance documents from lifestyle-patterns namespace only
        """
        if not self.is_available():
            logger.warning(f"[RAG] Lifestyle Patterns query skipped - RAG service not available")
            return []
        
        logger.info(f"[RAG] Lifestyle Patterns query initiated: '{query[:100]}...' (top_k={top_k})")
        logger.info(f"[RAG] NAMESPACE ISOLATION: Querying ONLY '{NAMESPACE_LIFESTYLE_PATTERNS}' namespace")
        
        # Enhance query with patient context
        enhanced_query = query
        if patient_context:
            context_parts = [query]
            if patient_context.get('age'):
                context_parts.append(f"age {patient_context['age']}")
            if patient_context.get('ethnicity'):
                context_parts.append(f"ethnicity {patient_context['ethnicity']}")
            if patient_context.get('conditions'):
                context_parts.append(f"conditions {', '.join(patient_context['conditions'])}")
            enhanced_query = " ".join(context_parts)
            logger.debug(f"[RAG] Enhanced query with patient context: '{enhanced_query[:150]}...'")
        
        # STRICT NAMESPACE ISOLATION: Only query lifestyle-patterns namespace
        results = self.search(enhanced_query, namespace=NAMESPACE_LIFESTYLE_PATTERNS, top_k=top_k)
        logger.info(f"[RAG] Lifestyle Patterns query returned {len(results)} results from namespace '{NAMESPACE_LIFESTYLE_PATTERNS}' ONLY")
        if results:
            logger.debug(f"[RAG] Top result source: {results[0].get('metadata', {}).get('source', 'Unknown')}")
        
        return results
    
    def ingest_with_metadata(
        self,
        documents: List[Dict[str, Any]],
        namespace: str,
        batch_size: int = 96,
    ) -> None:
        """Ingest documents with rich metadata for better retrieval.
        
        Args:
            documents: List of document dicts with keys: content, metadata (source, tags, etc.)
            namespace: Target namespace (clinical_safety, dietician_docs, lifestyle-patterns)
            batch_size: Batch size for upsert (max 96 for text)
        """
        if not self.is_available():
            logger.warning("Pinecone not configured. Skipping document ingestion.")
            return
        
        try:
            # Prepare records
            records = []
            for doc in documents:
                # Use "text" field to match index field_map (text=content)
                record = {
                    "_id": doc.get("id", f"{namespace}_{len(records)}"),
                    "text": doc["content"].strip(),  # Index expects "text" field
                }
                # Add metadata fields
                metadata = doc.get("metadata", {})
                if metadata:
                    # Store metadata in fields (Pinecone integrated embeddings)
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            record[key] = value
                        elif isinstance(value, list):
                            record[key] = ", ".join(str(v) for v in value)
                        else:
                            record[key] = str(value)
                
                records.append(record)
            
            # Upsert in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                self.index.upsert_records(namespace, batch)
                logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} records) to namespace '{namespace}'")
                time.sleep(0.1)  # Rate limiting
            
            # Wait for indexing
            logger.info(f"Waiting 10 seconds for vectors to be indexed...")
            time.sleep(10)
            logger.info(f"Successfully ingested {len(records)} documents into namespace '{namespace}'")
            
        except PineconeException as e:
            logger.error(f"Pinecone error during ingestion: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during ingestion: {e}", exc_info=True)
            raise


@lru_cache(maxsize=1)
def get_rag_service(index_name: Optional[str] = None) -> RAGService:
    """Get singleton RAG service instance.
    
    Args:
        index_name: Optional index name override
        
    Returns:
        RAGService instance
    """
    return RAGService(index_name=index_name)
