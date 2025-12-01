import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.graph.pipeline import AIPipeline
from src.graph.nodes import PipelineNodes

class TestAIPipeline:
    
    @pytest.fixture
    def pipeline(self):
        with patch('streamlit.session_state', MagicMock()):
            return AIPipeline()
    
    @pytest.mark.asyncio
    async def test_process_weather_query(self, pipeline):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(pipeline.nodes, 'fetch_weather') as mock_weather:
                mock_weather.return_value = {
                    "query": "What's the weather in London?",
                    "query_type": "weather",
                    "weather_data": Mock(),
                    "response": "Weather in London: 22°C, partly cloudy",
                    "next_node": "response_generation"
                }
                
                with patch.object(pipeline.nodes, 'generate_response') as mock_response:
                    mock_response.return_value = {
                        "response": "Weather in London: 22°C, partly cloudy"
                    }
                    
                    result = await pipeline.process_query("What's the weather in London?")
                    
                    assert result["success"] is True
                    assert result["query_type"] == "weather"
    
    @pytest.mark.asyncio
    async def test_process_document_query(self, pipeline):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(pipeline.nodes, 'search_documents') as mock_search:
                mock_search.return_value = {
                    "query": "What is AI?",
                    "query_type": "document",
                    "search_results": [{"content": "AI is transformative"}],
                    "next_node": "response_generation"
                }
                
                with patch.object(pipeline.nodes, 'generate_response') as mock_response:
                    mock_response.return_value = {
                        "response": "Based on the documents, AI is transformative"
                    }
                    
                    result = await pipeline.process_query("What is AI?")
                    
                    assert result["success"] is True
                    assert result["query_type"] == "document"
    
    @pytest.mark.asyncio
    async def test_load_pdf(self, pipeline):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(pipeline.nodes, 'load_pdf_documents') as mock_load:
                mock_load.return_value = True
                
                result = await pipeline.load_pdf("test.pdf")
                
                assert result is True
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status(self, pipeline):
        with patch('streamlit.session_state', MagicMock()):
            with patch.object(pipeline.nodes.vector_service, 'get_collection_info') as mock_info:
                mock_info.return_value = {
                    "points_count": 10,
                    "indexed_vectors_count": 10,
                    "status": "green"
                }
                
                result = await pipeline.get_pipeline_status()
                
                assert result["pipeline_status"] == "active"
                assert result["vector_database"]["documents_count"] == 10
