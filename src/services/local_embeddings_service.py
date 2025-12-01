"""
Local embeddings service using sentence-transformers.
Completely free - no API costs!
"""

import structlog
from typing import List
import asyncio
from sentence_transformers import SentenceTransformer
import numpy as np

logger = structlog.get_logger()

# Singleton instance
_embeddings_service_instance = None
_model_instance = None

def get_embeddings_service():
    """Get or create the embeddings service using session state."""
    import streamlit as st
    
    if 'embeddings_service' not in st.session_state:
        st.session_state.embeddings_service = LocalEmbeddingsService()
        logger.info("Created new embeddings service in session state")
    else:
        logger.info("Using existing embeddings service from session state")
    
    return st.session_state.embeddings_service

class LocalEmbeddingsService:
    """Local embeddings service using sentence-transformers."""
    
    def __init__(self):
        """Initialize the local embeddings model."""
        try:
            import streamlit as st
            use_streamlit = True
        except ImportError:
            use_streamlit = False
        
        self.model_name = "all-MiniLM-L6-v2"  # Good balance of speed and quality
        self.embedding_dimension = 384  # Dimension for this model
        
        # Use session state for model instance to avoid reloading (if Streamlit available)
        if use_streamlit and 'embeddings_model' not in st.session_state:
            self._load_model()
            st.session_state.embeddings_model = self.model
            logger.info(f"Loaded and cached embeddings model: {self.model_name}")
        elif use_streamlit:
            self.model = st.session_state.embeddings_model
            logger.info(f"Using cached embeddings model: {self.model_name}")
        else:
            # Direct initialization without Streamlit
            self._load_model()
            logger.info(f"Loaded embeddings model directly: {self.model_name}")
    
    def _load_model(self):
        """Load the sentence-transformers model."""
        try:
            # Load model with device='cpu' to avoid meta tensor issues
            self.model = SentenceTransformer(self.model_name, device='cpu')
            
            # Test the model with a simple encoding to ensure it works
            test_embedding = self.model.encode("test", show_progress_bar=False)
            logger.info(f"Loaded local embeddings model: {self.model_name}")
            logger.info(f"Model test successful - embedding dimension: {len(test_embedding)}")
        except Exception as e:
            logger.error(f"Failed to load embeddings model: {str(e)}")
            # Try alternative loading method
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded local embeddings model (alternative method): {self.model_name}")
            except Exception as e2:
                logger.error(f"Failed to load embeddings model with alternative method: {str(e2)}")
                raise
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a given text using local model.
        
        Args:
            text: Text to create embedding for
            
        Returns:
            List of embedding values
        """
        if not self.model:
            logger.error("Embeddings model not loaded")
            return []
        
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []
        
        try:
            # Run the synchronous model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                self.model.encode, 
                text
            )
            
            # Convert numpy array to list
            embedding_list = embedding.tolist()
            
            # Ensure we have the correct dimension
            if len(embedding_list) != self.embedding_dimension:
                logger.warning(f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {len(embedding_list)}")
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error creating local embedding: {str(e)}")
            return []
    
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts at once (more efficient).
        
        Args:
            texts: List of texts to create embeddings for
            
        Returns:
            List of embedding lists
        """
        if not self.model:
            logger.error("Embeddings model not loaded")
            return []
        
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []
        
        try:
            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                return []
            
            # Run batch encoding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.model.encode,
                valid_texts
            )
            
            # Convert to list of lists
            embedding_lists = embeddings.tolist()
            
            logger.info(f"Created {len(embedding_lists)} batch embeddings")
            return embedding_lists
            
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {str(e)}")
            return []
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self.embedding_dimension
    
    def is_available(self) -> bool:
        """Check if the embeddings service is available."""
        return self.model is not None
