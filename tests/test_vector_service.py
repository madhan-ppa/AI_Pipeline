import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.services.vector_service import VectorService
from src.services.pdf_service import PDFService, PDFChunk

class TestVectorService:
    
    @pytest.fixture
    def vector_service(self):
        with patch('streamlit.session_state', MagicMock()):
            return VectorService()
    
    @pytest.fixture
    def sample_chunks(self):
        return [
            PDFChunk(
                content="AI is a transformative technology",
                page_number=1,
                chunk_index=0,
                metadata={}
            ),
            PDFChunk(
                content="Machine learning is a subset of AI",
                page_number=1,
                chunk_index=1,
                metadata={}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_store_pdf_chunks(self, vector_service, sample_chunks):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(vector_service, 'store_pdf_chunks', new_callable=AsyncMock) as mock_store:
                mock_store.return_value = True
                
                result = await mock_store(sample_chunks)
                
                assert result is True
    
    @pytest.mark.asyncio
    async def test_search_similar_documents(self, vector_service):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(vector_service, 'search_similar_documents', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = [
                    {
                        "content": "AI is transformative",
                        "page_number": 1,
                        "chunk_index": 0,
                        "score": 0.8
                    }
                ]
                
                result = await mock_search("What is AI?")
                
                assert len(result) == 1
                assert result[0]["content"] == "AI is transformative"
                assert result[0]["score"] == 0.8
    
    def test_format_search_results(self, vector_service):
        with patch('streamlit.session_state', MagicMock()):
            search_results = [
                {
                    "content": "AI is transformative",
                    "page_number": 1,
                    "chunk_index": 0,
                    "score": 0.8
                }
            ]
            
            formatted = vector_service.format_search_results(search_results)
            
            assert "AI is transformative" in formatted
            assert "Page 1" in formatted
