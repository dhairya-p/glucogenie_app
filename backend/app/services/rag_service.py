"""RAG service for medical knowledge retrieval using Pinecone."""
from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Any, Optional

from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone.exceptions import PineconeException

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


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
        return self.index is not None
    
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
                "content": doc.strip(),
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
        
        Args:
            query: Search query text
            index_type: Filter by knowledge type (e.g., 'drug', 'food', 'clinical')
            top_k: Number of results to return
            namespace: Optional namespace to search. Defaults to index_type if provided
            
        Returns:
            List of search results with content, score, and metadata
        """
        if not self.is_available():
            logger.warning("Pinecone not configured. Returning empty results.")
            return []
        
        namespace = namespace or index_type or "general"
        
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
            
            # Perform search with reranking for better results
            results = self.index.search(
                namespace=namespace,
                query=query_dict,
                rerank={
                    "model": "bge-reranker-v2-m3",
                    "top_n": top_k,
                    "rank_fields": ["content"]
                }
            )
            
            # Format results
            formatted_results = []
            for hit in results.result.hits:
                formatted_results.append({
                    "id": hit["_id"],
                    "content": hit.fields["content"],
                    "score": hit["_score"],
                    "metadata": {
                        "index_type": hit.fields.get("index_type", "unknown")
                    }
                })
            
            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
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
        index_types: Optional[list[str]] = None,
        top_k: int = 3,
    ) -> str:
        """Get formatted context string for LLM prompt.
        
        Args:
            query: Search query
            index_types: List of knowledge types to search (e.g., ['drug', 'food'])
                        If None, searches all namespaces
            top_k: Number of results per index type
            
        Returns:
            Formatted context string with citations
        """
        if not self.is_available():
            return ""
        
        all_results = []
        
        if index_types:
            # Search specific index types
            for index_type in index_types:
                results = self.search(query, index_type=index_type, top_k=top_k)
                all_results.extend(results)
        else:
            # Search all namespaces (general, drug, food, clinical)
            for namespace in ["general", "drug", "food", "clinical"]:
                results = self.search(query, namespace=namespace, top_k=top_k)
                all_results.extend(results)
        
        # Sort by score and take top results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:top_k * 2]  # Get top results across all types
        
        # Format as context string
        if not top_results:
            return ""
        
        context_parts = ["Relevant Medical Knowledge:"]
        for idx, result in enumerate(top_results, 1):
            context_parts.append(
                f"[{idx}] {result['content']} (Source: {result['metadata']['index_type']})"
            )
        
        return "\n".join(context_parts)


@lru_cache(maxsize=1)
def get_rag_service(index_name: Optional[str] = None) -> RAGService:
    """Get singleton RAG service instance.
    
    Args:
        index_name: Optional index name override
        
    Returns:
        RAGService instance
    """
    return RAGService(index_name=index_name)
