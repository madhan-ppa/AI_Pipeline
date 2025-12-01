import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.llm_service import OpenRouterLLMService

class TestOpenRouterLLMService:
    
    @pytest.fixture
    def llm_service(self):
        return OpenRouterLLMService()
    
    @pytest.mark.asyncio
    async def test_simple_chat_success(self, llm_service):
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Test response"}}]
            })
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            
            result = await llm_service.simple_chat("Test message")
            
            assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_analyze_weather_query(self, llm_service):
        with patch.object(llm_service, 'simple_chat') as mock_chat:
            mock_chat.return_value = "The weather in London is pleasant with 22°C temperature"
            
            weather_data = {
                "city": "London",
                "temperature": 22.5,
                "feels_like": 24.0,
                "description": "partly cloudy",
                "humidity": 65,
                "wind_speed": 3.5
            }
            
            result = await llm_service.analyze_weather_query(weather_data)
            
            assert result is not None
            assert "London" in result
    
    @pytest.mark.asyncio
    async def test_analyze_document_query(self, llm_service):
        with patch.object(llm_service, 'simple_chat') as mock_chat:
            mock_chat.return_value = "Based on the documents, AI is a transformative technology"
            
            result = await llm_service.analyze_document_query(
                "What is AI?", 
                "AI stands for Artificial Intelligence"
            )
            
            assert result is not None
            assert "AI" in result
