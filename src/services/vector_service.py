"""
Vector service for managing embeddings and vector search using Qdrant.
"""

import uuid
import asyncio
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchText

from src.config import Config
from src.services.pdf_service import PDFChunk
from src.services.local_embeddings_service import get_embeddings_service

logger = structlog.get_logger()

# Singleton instance for VectorService
_vector_service_instance = None

def get_vector_service():
    """Get or create the VectorService instance using session state."""
    import streamlit as st
    
    if 'vector_service' not in st.session_state:
        st.session_state.vector_service = VectorService()
        logger.info("Created new VectorService in session state")
    else:
        logger.info("Using existing VectorService from session state")
    
    return st.session_state.vector_service

@dataclass
class VectorDocument:
    """Document structure for vector storage."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]

class VectorService:
    """Service for managing embeddings and vector search using Qdrant."""
    
    def __init__(self):
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self.embedding_dimension = Config.EMBEDDING_DIMENSION
        self.search_limit = Config.VECTOR_SEARCH_LIMIT
        
        # Initialize Qdrant client with fallback
        self.client = None
        self.use_in_memory = False
        
        if Config.QDRANT_URL:
            try:
                # For local Qdrant, no API key needed
                if Config.QDRANT_URL.startswith("http://localhost") or Config.QDRANT_URL.startswith("http://127.0.0.1"):
                    self.client = QdrantClient(url=Config.QDRANT_URL, timeout=10)
                    # Test connection
                    self.client.get_collections()
                    logger.info(f"Connected to local Qdrant at {Config.QDRANT_URL}")
                else:
                    # For remote Qdrant, use API key if provided
                    self.client = QdrantClient(
                        url=Config.QDRANT_URL,
                        api_key=Config.QDRANT_API_KEY,
                        timeout=10
                    )
                    logger.info(f"Connected to remote Qdrant at {Config.QDRANT_URL}")
            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant at {Config.QDRANT_URL}: {str(e)}")
                logger.info("Falling back to in-memory Qdrant")
                self.client = None
                self.use_in_memory = True
        
        # Use in-memory Qdrant for development or as fallback
        if self.client is None:
            self.client = QdrantClient(":memory:")
            self.use_in_memory = True
            logger.info("Using in-memory Qdrant for development")
        
        # Initialize local embeddings service (free!)
        self.embeddings_service = get_embeddings_service()
        
        # Update embedding dimension from local service
        self.embedding_dimension = self.embeddings_service.get_embedding_dimension()
        
        # Flag to track if collection has been ensured
        self._collection_ensured = False
        
        # Disable fastembed to use our local embeddings instead
        self.client._fastembed_wrapper = None
    
    async def _ensure_collection(self):
        """Ensure the Qdrant collection exists."""
        if self._collection_ensured:
            return
            
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            
            self._collection_ensured = True
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a given text using local sentence-transformers.
        
        Args:
            text: Text to create embedding for
            
        Returns:
            List of embedding values
        """
        return await self.embeddings_service.create_embedding(text)
    
    async def store_pdf_chunks(self, chunks: List[PDFChunk]) -> bool:
        """
        Store PDF chunks in vector database using batch embeddings for efficiency.
        
        Args:
            chunks: List of PDFChunk objects to store
            
        Returns:
            True if successful, False otherwise
        """
        if not chunks:
            logger.warning("No chunks to store")
            return False
        
        # Ensure collection exists before storing
        await self._ensure_collection()
        
        try:
            # Extract text content for batch embedding
            texts = [chunk.content for chunk in chunks]
            
            # Create embeddings in batch (more efficient)
            embeddings = await self.embeddings_service.create_embeddings_batch(texts)
            
            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
                return False
            
            # Create points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if not embedding:
                    continue
                
                # Create valid UUID for point ID
                point_id = str(uuid.uuid4())
                
                # Create point for Qdrant
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "source_filename": os.path.basename(chunk.metadata.get("source", "unknown"))
                    }
                )
                points.append(point)
            
            if not points:
                logger.warning("No valid points created from chunks")
                return False
            
            # Upload in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
            
            logger.info(f"Stored {len(points)} PDF chunks in vector database")
            return True
        
        except Exception as e:
            logger.error(f"Error storing PDF chunks: {str(e)}")
            return False
    
    async def search_similar_documents(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents based on query.
        
        Args:
            query: Search query
            limit: Maximum number of results (default uses config)
            
        Returns:
            List of similar documents with metadata
        """
        # Ensure collection exists before searching
        await self._ensure_collection()
        
        try:
            # Create embedding for query
            query_embedding = await self.create_embedding(query)
            if not query_embedding:
                return []
            
            # Search in Qdrant using our local embeddings
            search_limit = limit or self.search_limit
            
            # Try different query methods based on what's available
            try:
                from qdrant_client.models import NearestQuery
                query_response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=NearestQuery(
                        nearest=query_embedding
                    ),
                    limit=search_limit,
                    with_payload=True
                )
                results = query_response.points  # Extract points from QueryResponse
                logger.info("Successfully used NearestQuery method")
            except ImportError:
                # Fallback: try direct query_points with vector
                logger.warning("NearestQuery not available, trying direct vector query")
                try:
                    query_response = self.client.query_points(
                        collection_name=self.collection_name,
                        query=query_embedding,  # Direct vector
                        limit=search_limit,
                        with_payload=True
                    )
                    results = query_response.points  # Extract points from QueryResponse
                    logger.info("Successfully used direct vector query")
                except Exception as e:
                    # Last resort: use query method with our embeddings
                    logger.warning(f"Direct vector query failed ({str(e)}), trying query method")
                    try:
                        # Configure client to use our embeddings model
                        if not hasattr(self.client, '_embedding_model') or self.client._embedding_model is None:
                            # Set up our embeddings model for fastembed
                            self.client._embedding_model = self.embeddings_service.model
                            logger.info("Configured client with local embeddings model")
                        
                        query_response = self.client.query(
                            collection_name=self.collection_name,
                            query_text=query,
                            limit=search_limit,
                            with_payload=True
                        )
                        results = query_response.points  # Extract points from QueryResponse
                        logger.info("Successfully used query method with local embeddings")
                    except Exception as e2:
                        logger.error(f"All query methods failed: {str(e2)}")
                        return []
            
            # Format results
            documents = []
            for result in results:
                # Handle different result formats
                if hasattr(result, 'payload'):
                    payload = result.payload
                    score = result.score if hasattr(result, 'score') else 0.0
                elif isinstance(result, tuple) and len(result) >= 2:
                    # Tuple format: (point, score)
                    point, score = result[0], result[1]
                    payload = point.payload if hasattr(point, 'payload') else {}
                else:
                    continue
                
                documents.append({
                    "content": payload.get("content", ""),
                    "page_number": payload.get("page_number", 0),
                    "source": payload.get("source_filename", payload.get("metadata", {}).get("source", "Unknown")),
                    "score": score,
                    "chunk_index": payload.get("chunk_index", 0)
                })
            
            logger.info(f"Found {len(documents)} similar documents for query: {query[:50]}...")
            return documents
        
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the vector collection."""
        try:
            if self.use_in_memory:
                return {
                    "name": self.collection_name,
                    "type": "in-memory",
                    "status": "active",
                    "note": "Using in-memory Qdrant (data not persisted)"
                }
            
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "type": "remote"
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {
                "name": self.collection_name,
                "type": "in-memory" if self.use_in_memory else "remote",
                "status": "error",
                "error": str(e)
            }
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a readable response."""
        if not results:
            return "No relevant information found in the documents."
        
        response = "Found relevant information:\n\n"
        for i, result in enumerate(results, 1):
            source = os.path.basename(result.get("source", "Unknown"))
            page = result.get("page_number", 0)
            score = result.get("score", 0)
            content = result.get("content", "")
            
            response += f"**Source {i}:** {source} (Page {page}, Score: {score:.3f})\n"
            response += f"{content[:500]}{'...' if len(content) > 500 else ''}\n\n"
        
        return response
